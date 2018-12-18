# -*- coding: utf-8 -*-
# Copyright (C) 2016, 2017, 2018  Jason Sydes and Peter Batzel
#
# This file is part of Dupligänger.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the License with this program.
#
# Written by Jason Sydes
# Conceptual Design by Peter Batzel and Jason Sydes

"""Splits raw sequencing FASTQs by barcode, quality filters, and annotated UMIs.

Usage:
    dupliganger barcode-split-quality-filter-umi-anno [options] <barcode_file> <in.fq> <in.barcode.fq> <in.umi.fq>
    dupliganger barcode-split-quality-filter-umi-anno [options] <barcode_file> <in.R1.fq> <in.R2.fq> <in.barcode.fq> <in.umi.fq>

Input:
    This utility works on FASTQ files produced by Illumina's bcl2fastq2.  It
    assumes that it was a paired-end sequencing run with the following files:
        * <in.R1.fq> - Read 1.
        * <in.R2.fq> - Read 2.
        * <in.barcode.fq> - The barcode for the read pair.
        * <in.umi.fq> - The UMI of the barcode.
    You'll need to speak with your sequencing facility to determine which files
    are which.  For example, our facility has produced files that look like this:
        * Undetermined_S0_R1_* - This is Read 1.
        * Undetermined_S0_R2_* - This is the barcode.
        * Undetermined_S0_R3_* - This is the UMI.
        * Undetermined_S0_R4_* - This is Read 2.
    You'll also need to provide a list of barcodes used (<barcode_file>).  See
    below.

Barcodes and Output File Names:
    You'll need to pass a list of expected barcodes in <barcode_file>.  Put one
    barcode per line in this file; alternatively, you may put a barcode
    followed by whitespace followed by a sample name (no spaces in sample names
    allowed). If you take the former approach, output files will be named after
    their barcodes; if you take the latter approach, output files will be named
    after your samples.  Reads that don't match any barcode are placed in a
    rejects file.

UMI quality and quailty filtering:
    If an UMI has an 'N' in its sequence, this utility will reject it and write
    it to the rejects files.

    Additionally, by default, Dupligänger quality filters out any read that
    has an average quality score less than 30 across a window size of 1. You
    can change those parameters with -w and -q respectively.  Alternatively,
    you can disable UMI quality filtering altogether by setting either -w or -q
    to '0'.

Note:
    Dupligänger supports (and autodetects) input FASTQ files that are gzipped.

Options:
    -h, --help
    -v, --verbose               Be verbose.
    -o OUT_DIR                  Place results in directory OUT_DIR.
    --phred PHRED               How FASTQ phred scores are encoded [default: 33].
                                Default is '33'. Use '64' to specify phred64
                                encoding.
    -w W, --umi-qf-win-size W   Set window size of 'W' nucleotides for UMI
                                quality filtering. See notes above. Disable
                                quality filtering by setting -w or -q to 0.
                                [default: 1].
    -q Q, --umi-min-qual Q      Set minimum average quality score 'Q' for UMI
                                quality filtering across window size 'W'
                                nucleotides for UMI.  See notes above. Disable
                                quality filtering by setting -w or -q to 0.
                                [default: 30].
    -T, --no-delete-tmp-files   Upon some failure, do *not* delete the
                                temporary files created by this utility.
    -r, --no-write-rejects      Do not write files of reads rejected due to
                                mismatching barcodes, 'N's in UMIs, or
                                low-quality UMIs.
"""

###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division
from builtins import range

# Dupligänger imports
from dupliganger.constants import *
from dupliganger.exceptions import *
from dupliganger.common import (args_to_out_dir, pgopen, is_gzipped, gzwrite,
        tmpf_start, tmpf_finish, tmpf_open, filename_in_to_out_fqgz)

## Other imports
from docopt import docopt

# for opening up files (e.g. open_out_pe_barcode_fastq_files)
import contextlib

# For filename fixing
import os

# For writing gzipped files
import gzip

# For checking presence of illumina index under python 2/3.
import io

# For shell-like "which()"
try:
    from shutil import which
except ImportError:
    from whichcraft import which

# For function partials
import functools


#################
### Constants ###
#################


#################
### Functions ###
#################

def parse_barcode_list_file(barcode_list_file):
    """Parse the barcodes list file. It can come in several different formats.
    Autodetect which format, and return a dict mapping barcode to optional
    sample name.  If sample names are not given, all vals are ...????.

    Example format 1:
        ACGTGGGG
        TTAATTCC

    Example format 2:
        ACGTGGGG    SampleName1
        TTAATTCC    SampleName2

    Example format 3:
        SampleName1     ACGTGGGG
        SampleName2     TTAATTCC

    Args:
        barcode_list_file (str): Name of the barcodes list file.
    Returns:
        (dict): keys: barcodes (str), vals: None (None) or sample name (str).
    """
    lines = []
    with pgopen(1, barcode_list_file) as bcf:
        for line in bcf:
            line = line.strip()
            if line == '' or line[0] == '#':
                # skip blank lines and comments
                continue
            lines.append(line)

    # Determine number of columns in file (and confirm all lines have same
    # number of columns)
    num_cols = set()
    for line in lines:
        num_cols.add(len(line.strip().split()))
    if len(num_cols) == 0:
        raise CannotContinueException(
                """ERR808: Barcodes list file is empty?""")
    elif len(num_cols) > 1:
        raise CannotContinueException(
                """ERR801: Cannot parse barcodes file, mix of number of columns?""")
    num_cols = list(num_cols)[0]

    # keys: barcodes (str), vals: None (None) or sample name (str).
    barcodes_list_dict = {}
    if num_cols == 1:
        # Example format 1
        for bc in lines:
            barcodes_list_dict[bc] = None
    elif num_cols == 2:
        # Example format 2 or 3.  Which one?
        chars1 = ''
        chars2 = ''
        barcodes_in_col = None
        # First, figure out which column barcodes are in.
        for line in lines:
            c1, c2 = line.split()
            chars1 += c1
            chars2 += c2
        chars1 = chars1.strip('ACGT')
        chars2 = chars2.strip('ACGT')
        if (chars1 == '' and chars2 == ''):
            raise CannotContinueException(
                    "ERR678: Cannot parse barcodes file. Did you put barcodes "
                    "in both columns?  If using two columns, place barcodes in "
                    "one column, and sample names in the other column.")
        elif chars1 != '' and chars2 != '':
            raise CannotContinueException(
                    "ERR876: Cannot parse barcodes file. Please put barcodes in "
                    "one column and sample names in another column. Please note "
                    "that no spaces are allowed in sample names.")
        elif chars1 == '' and chars2 != '':
            barcodes_in_col = 1
        elif chars1 != '' and chars2 == '':
            barcodes_in_col = 2

        # Now parse it
        if barcodes_in_col == 1:
            # Example format 2
            for line in lines:
                bc, name = line.split()
                barcodes_list_dict[bc] = name
        else:
            # Example format 3
            for line in lines:
                name, bc = line.split()
                barcodes_list_dict[bc] = name

    return barcodes_list_dict

@contextlib.contextmanager
def open_out_pe_barcode_fastq_files(outdir, delete_temp_files_upon_failure,
        fp_write, barcode_list_dict):
    """Context manager to help manage the variable number of output paired-end
    FASTQ files.  Takes as input a list of barcodes.  Based upon the list of
    barcodes (or optionally mapped sample names if provided in
    barcode_list_dict), does the following:
        * opens *temporary* paired-end output files for writing, two for each
          barcode.
        * yields those back for writing
        * when finished writing, closes the files.
        * renames the temporary files to be named after barcodes (or sample
          names if provided).

    Args:
        outdir (str): Place output fastq files in directory outdir.
        delete_temp_files_upon_failure (bool): If there is a failure and this
            arg is True, delete the temp files.
        fp_write (function): Function pointer for writing output files.
        barcode_list_dict (dict): Keys are expected barcodes, vals are either
            None or sample names.
    Yields:
        (dict): Each key is a barcode, each value is a two-tuple of file handles
            for that barcode (first fh is R1 output file for that barcode,
            second fh is for R2).
    """
    # keys: barcodes, vals: [read1_tmp_filehandle, read2_tmp_filehandle]
    output_files = {}
    tmp_output_filenames = {}

    try:
        ## This 'try' block: open output files for writing, yield.

        for barcode, opt_sample_name in barcode_list_dict.items():
            # First, determine if we're using barcodes or sample names for
            # final file names ('pretend' is here just so we can reuse
            # filename_in_to_out_fqgz...)
            if opt_sample_name is not None:
                in_pretend_r1 = "{}.R1.fq".format(opt_sample_name)
                in_pretend_r2 = "{}.R2.fq".format(opt_sample_name)
            else:
                in_pretend_r1 = "{}.R1.fq".format(barcode)
                in_pretend_r2 = "{}.R2.fq".format(barcode)

            # Come up with final filenames, open temp versions of those files,
            # record file names for later use....
            out_r1 = filename_in_to_out_fqgz(in_pretend_r1, SUFFIX_REMOVE_UMI,
                    False, outdir)
            out_r2 = filename_in_to_out_fqgz(in_pretend_r2, SUFFIX_REMOVE_UMI,
                    False, outdir)
            tmp_out_r1, tmp_out_r2 = tmpf_start(out_r1, out_r2)

            tmp_output_filenames[barcode] = (tmp_out_r1, tmp_out_r2)
            output_files[barcode] = (fp_write(tmp_out_r1), fp_write(tmp_out_r2))

        yield output_files

    except Exception as e:
        ## This 'except' block: try to recover from failure (close/delete files)
        for barcode in barcode_list_dict:
            # Close tmp files first
            for out_f in output_files[barcode]:
                try:
                    out_f.close()
                except Exception:
                    pass
            if delete_temp_files_upon_failure:
                for tmp_filename in tmp_output_filenames[barcode]:
                    try:
                        os.remove(tmp_filename)
                    except Exception:
                        pass
        raise e

    finally:
        ## This 'finally' block: normal exit, close/rename files.
        for barcode in barcode_list_dict:
            # Close tmp files first
            for out_f in output_files[barcode]:
                out_f.close()
            # Rename from tmp to final...
            tmp_out_r1, tmp_out_r2 = tmp_output_filenames[barcode]
            try:
                tmpf_finish(tmp_out_r1, tmp_out_r2)
            except Exception:
                # We catch and ignore this exception so as to not mask previous exceptions.
                pass

def split_qf_umi_anno_raw_pe(in_r1, in_r2, in_bc, in_umi, out_rejects_r1,
        out_rejects_r2, out_rejects_bc, out_rejects_umi, out_files,
        barcodes_list_dict, phred, min_umi_qual, umi_qf_win_size,
        write_rejects_files):
    """Using non-barcode-split (ie 'raw') FASTQ files from Illumina's
    bcl2fastq2 (paired-end version) as input, split by barcode, then quality
    filter on UMI, then create paired FASTQ output files with read name
    annotated with UMI.

    ASSUMPTION:
        All reads ID lines have two fields and look something like this:
          @EAS139:136:FC706VJ:2:5:1000:12850 1:N:0

    Args:
        in_r1 (file): Read1 input fastq file handle.
        in_r2 (file): Read2 input fastq file handle.
        in_bc (file): FASTQ file handle of barcodes.
        in_umi (file): FASTQ file handle of UMIs.
        out_rejects_r1 (file): Read1 rejects output fastq file handle.
        out_rejects_r2 (file): Read2 rejects output fastq file handle.
        out_rejects_bc (file): FASTQ output file handle of barcodes (rejects).
        out_rejects_umi (file): FASTQ output file handle of UMIs (rejects).
        out_files ([file]): Output paired-end fastq file handles.
        barcodes_list_dict (dict): Keys: barcodes, vals: optional sample name.
        phred (int): How quality scores are phred encoded (33 or 64).
        write_rejects_files (bool): Whether or not to write rejects files.
    """
    fq_rec = "{}\n{}\n+\n{}\n"

    # For report
    hist_barcodes = {}
    hist_umis = {}
    count_barcode_mismatch = 0
    count_umi_has_N = 0
    count_umi_failed_qf = 0

    # Assume that you've already setup a bunch of stuff already...
    while True:
        name1, seq1, _, qual1 = \
                (in_r1.readline().rstrip() for i in range(4))
        name2, seq2, _, qual2 = \
                (in_r2.readline().rstrip() for i in range(4))
        name_bc, seq_bc, _, qual_bc = \
                (in_bc.readline().rstrip() for i in range(4))
        name_umi, seq_umi, _, qual_umi = \
                (in_umi.readline().rstrip() for i in range(4))

        if not name1:
            # EOF
            break

        # record for report
        if seq_bc not in barcodes_list_dict:
            count_barcode_mismatch += 1
        elif 'N' in seq_umi:
            count_umi_has_N += 1

        if seq_bc not in barcodes_list_dict or 'N' in seq_umi:
            # Barcode doesn't match, or 'N' in UMI sequence. Write to rejects
            # files.

            if write_rejects_files:
                out_rejects_r1.write(fq_rec.format(name1, seq1, qual1))
                out_rejects_r2.write(fq_rec.format(name2, seq2, qual2))
                out_rejects_bc.write(fq_rec.format(name_bc, seq_bc, qual_bc))
                out_rejects_umi.write(fq_rec.format(name_umi, seq_umi, qual_umi))
            continue
        else:
            # Begin quality filter UMI.
            umi_failed_qf = False
            if min_umi_qual > 0 and umi_qf_win_size > 0:
                start = 0
                stop = umi_qf_win_size
                len_qual_umi = len(qual_umi)
                while stop <= len_qual_umi and not umi_failed_qf:
                    qual_sum = 0
                    for char in qual_umi[start:stop]:
                        qual_sum += ord(char) - phred
                    if (qual_sum/(stop-start) < min_umi_qual):
                        umi_failed_qf = True
                        break
                    start += 1
                    stop += 1
            # End quality filter

            if umi_failed_qf:
                # UMI failed quality filter. Write to rejects files.
                count_umi_failed_qf += 1
                if write_rejects_files:
                    out_rejects_r1.write(fq_rec.format(name1, seq1, qual1))
                    out_rejects_r2.write(fq_rec.format(name2, seq2, qual2))
                    out_rejects_bc.write(fq_rec.format(name_bc, seq_bc, qual_bc))
                    out_rejects_umi.write(fq_rec.format(name_umi, seq_umi, qual_umi))
                continue

        # Read pair has good barcode and UMI. Continue along...

        # record for report
        hist_barcodes.setdefault(seq_bc, 0)
        hist_barcodes[seq_bc] += 1
        hist_umis.setdefault(seq_umi, 0)
        hist_umis[seq_umi] += 1

        # Split the ID line into just the name and the 'info' field.
        # ASSUMPTION: All reads ID lines have two fields and look something
        # like this:
        #       @EAS139:136:FC706VJ:2:5:1000:12850 1:N:0
        just_name1, info1 = name1.split()
        just_name2, info2 = name2.split()
        just_name_bc, _ = name_bc.split()
        just_name_umi, _ = name_umi.split()

        # Confirm names are same.
        if just_name1 != just_name2:
            raise ParseException(
                    'R1 read name != R2 read name! ({} != {})'.format(
                        just_name1, just_name2))
        if just_name1 != just_name_bc:
            raise ParseException(
                    'R1 read name != barcode read name! ({} != {})'.format(
                        just_name1, just_name_bc))
        if just_name1 != just_name_umi:
            raise ParseException(
                    'R1 read name != UMI read name! ({} != {})'.format(
                        just_name1, just_name_umi))

        # Build the records
        name_anno = "{}{}{}".format(just_name1, DELIM_ANNO, seq_umi)
        info_anno1 = "{}:{}".format(info1, seq_bc)
        info_anno2 = "{}:{}".format(info2, seq_bc)
        record1 = "{} {}\n{}\n+\n{}\n".format(name_anno, info_anno1, seq1,
                qual1)
        record2 = "{} {}\n{}\n+\n{}\n".format(name_anno, info_anno2, seq2,
                qual2)

        out_files[seq_bc][0].write(record1)
        out_files[seq_bc][1].write(record2)

    return (hist_barcodes, hist_umis, count_barcode_mismatch, count_umi_has_N,
            count_umi_failed_qf)

def parse_args(args):
    """Parse the command line arguments. """

    umi_reads_file = os.path.expanduser(args['<in.umi.fq>'])
    barcode_reads_file = os.path.expanduser(args['<in.barcode.fq>'])
    barcode_list_file = os.path.expanduser(args['<barcode_file>'])
    delete_temp_files_upon_failure = not args['--no-delete-tmp-files']
    write_rejects_files = not args['--no-write-rejects']
    min_umi_qual = int(args['--umi-min-qual'])
    umi_qf_win_size = int(args['--umi-qf-win-size'])


    # phred
    if args['--phred'] not in ('33', '64'):
        raise ArgumentException("ERR212: --phred can be only '33' or '64'.")
    phred = int(args['--phred'])

    # Paired or single end?
    if args['<in.R2.fq>']:
        # mode = PE
        paired = True
        # Convert ~ to real path
        args['<in.R1.fq>'] = os.path.expanduser(args['<in.R1.fq>'])
        args['<in.R2.fq>'] = os.path.expanduser(args['<in.R2.fq>'])
        reads_files = [args['<in.R1.fq>'], args['<in.R2.fq>']]
    else:
        # Convert ~ to real path
        args['<in.fq>'] = os.path.expanduser(args['<in.fq>'])

        # mode = SR
        paired = False
        reads_files = [args['<in.fq>']]

    fp_write = functools.partial(open, mode = 'w')

    # Return an appropriate function pointer for annotation.
    if paired:
        fp_split_qf_umi_anno_raw = split_qf_umi_anno_raw_pe
    else:
        fp_split_qf_umi_anno_raw = split_qf_umi_anno_raw_sr

    outdir = args_to_out_dir(args)

    return (fp_split_qf_umi_anno_raw, fp_write, outdir, phred, min_umi_qual,
            umi_qf_win_size, write_rejects_files,
            delete_temp_files_upon_failure, barcode_list_file,
            barcode_reads_file, umi_reads_file, reads_files)

def run(fp_split_qf_umi_anno_raw, fp_write, outdir, phred, min_umi_qual,
        umi_qf_win_size, write_rejects_files, delete_temp_files_upon_failure,
        barcode_list_file, barcode_reads_file, umi_reads_file, reads_files):
    """Start the run.

    Args:
        fp_split_qs_umi_anno (Function): Function to be used to parse the FASTQ
            file(s) and produce output.
        fp_write (Function): Function to be used to write output file(s).
        outdir (str): Output directory for results
        phred (int): How quality scores are phred encoded (33 or 64).
        force_paired (bool): Whether user wants to force paired-end, even if
            if we didn't detect it.
        barcode_list_file (str): File of list of barcodes.
        barcode_reads_file (str): FASTQ file of barcodes.
        umi_reads_file (str): FASTQ file of UMIs.
        reads_files ([str]): Array of read or read pair FASTQ files to be parsed.
    """

    # Parse barcode_list_file, build barcode_list_dict.
    barcodes_list_dict = parse_barcode_list_file(barcode_list_file)

    # Some datasets have look like this:
    #       @NS500451:139:H5TV5AFXX:1:11101:3928:1111 1:N:0:ATCACGTT
    # Others like this:
    #       @NS500451:139:H5TV5AFXX:1:11101:3928:1111
    # Detect.
    if is_gzipped(reads_files[0]):
        with gzip.open(reads_files[0], mode='rt') as in1:
            first_line = in1.readline()
    else:
        with io.open(reads_files[0], mode='r', encoding='latin-1') as in1:
            first_line = in1.readline()
    has_index = True if len(first_line.split()) > 1 else False

    reports = None
    common_file_prefix = None
    out_files = []

    if len(reads_files) == 2:
        # paired-end
        infile1, infile2 = reads_files

        common_file_prefix = os.path.commonprefix((infile1, infile2))

        # Build up rejects filenames
        out_rejects_r1 = filename_in_to_out_fqgz(infile1, SUFFIX_REJECTS,
                False, outdir)
        out_rejects_r2 = filename_in_to_out_fqgz(infile2, SUFFIX_REJECTS,
                False, outdir)
        out_rejects_bc = filename_in_to_out_fqgz(barcode_reads_file,
                SUFFIX_REJECTS, False, outdir)
        out_rejects_umi = filename_in_to_out_fqgz(umi_reads_file,
                SUFFIX_REJECTS, False, outdir)

        out_files += [out_rejects_r1, out_rejects_r2, out_rejects_bc,
                out_rejects_umi]

        # quick alias
        rm = delete_temp_files_upon_failure
        # open files for reading and writing...
        with    pgopen(1, infile1) as in_r1, \
                pgopen(1, infile2) as in_r2, \
                pgopen(1, barcode_reads_file) as in_bc, \
                pgopen(1, umi_reads_file) as in_umi, \
                tmpf_open(fp_write, rm, out_rejects_r1) as tmp_out_rejects_r1, \
                tmpf_open(fp_write, rm, out_rejects_r2) as tmp_out_rejects_r2, \
                tmpf_open(fp_write, rm, out_rejects_bc) as tmp_out_rejects_bc, \
                tmpf_open(fp_write, rm, out_rejects_umi) as tmp_out_rejects_umi, \
                open_out_pe_barcode_fastq_files(outdir,
                        delete_temp_files_upon_failure, fp_write,
                        barcodes_list_dict) as barcode_out_files:

            reports = fp_split_qf_umi_anno_raw(in_r1, in_r2, in_bc, in_umi,
                    tmp_out_rejects_r1, tmp_out_rejects_r2, tmp_out_rejects_bc,
                    tmp_out_rejects_umi, barcode_out_files, barcodes_list_dict, phred,
                    min_umi_qual, umi_qf_win_size, write_rejects_files)

            (hist_barcodes, hist_umis, count_barcode_mismatch, count_umi_has_N,
                    count_umi_failed_qf) = reports

            # Translate/Record actual barcode out_files for tests
            for fhs in barcode_out_files.values():
                # a little hacky here...
                for fh in fhs:
                    tmp_filename = fh.name
                    size = len(".tmp.") + TMP_FILE_NAME_RANDOM_STR_SIZE
                    filename = tmp_filename[:-size]
                    out_files.append(filename)

    elif len(reads_files) == 1:
        # single-end
        raise Exception('NOT YET IMPLEMENTED!!! ')
    else:
        raise ControlFlowException(
                """ERR911: Not possible to be here.""")

    # write report file
    report_file = "{}.report".format(common_file_prefix)
    with open(report_file, 'w') as f:
        f.write("num_reads_with_barcode_mismatch: {}\n".format(
            count_barcode_mismatch))
        f.write("num_reads_with_Ns_in_UMI: {}\n".format(
            count_umi_has_N))
        f.write("num_reads_with_umi_poor_quality: {}\n".format(
            count_umi_failed_qf))
        f.write("Barcode_Histogram:\n")
        for bc in sorted(hist_barcodes.keys()):
            f.write("{}: {}\n".format(bc, hist_barcodes[bc]))
        f.write("UMI_Histogram:\n")
        for umi in sorted(hist_umis.keys()):
            f.write("{}: {}\n".format(umi, hist_umis[umi]))

    return out_files

###############
### Classes ###
###############


############
### Main ###
############

def main():
    args = docopt(__doc__)
    run(*parse_args(args))

# vim: softtabstop=4:shiftwidth=4:expandtab

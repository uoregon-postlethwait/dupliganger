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

"""Annotates read names with UMIs and clips inline UMIs if needed.

Usage:
    dupliganger remove-umi [options] <input.fastq>
    dupliganger remove-umi [options] <in1.fastq> <in2.fastq>
    dupliganger remove-umi [options] <input.bam>


Note:
    Dupligänger supports (and autodetects) input FASTQ files that are gzipped.

Note:
    If passing a paired-end BAM file, it needs to be sorted by read name
    (if not sorted, dupliganger will exit out when it detects mismatching
    adjacent records).

Options:
    -h, --help
    -v, --verbose         Be verbose
    -k KIT, --kit KIT     The kit used [default: bioo].
    -o OUT_DIR            Place results in directory OUT_DIR.
    --compress            Compress (gzip) output files.
    -t N, --threads N     EXPERIMENTAL: If pigz is installed and --threads is
                          specified, output FASTQ files will be compressed with
                          pigz -p <n>; otherwise, they will be left
                          uncompressed (as it simply takes too long to compress
                          with just gzip) [default: 1].
    --force-paired        Do not autodetect whether paired-end vs single-end,
                          instead force paired-end. Helpful fail safe if you
                          believe you have paired end data.
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
from dupliganger.common import (pgopen, bamopen, gzwrite, pigzwrite,
        tmpf_start, tmpf_finish, is_gzipped, is_bam, is_paired_bam,
        filename_in_to_out_fqgz, filename_in_bam_to_out_fqgz, args_to_out_dir)

## Other imports
from docopt import docopt

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

def create_annotated_file_from_bam(fp_extract_umi, in1, out1):
    """Using a single-end BAM file as input, convert to FASTQ output file
    with read name annotated with UMI.

    Args:
        fp_extract_umi (function): A function used to extract the UMI.
        in1 (file): Single-end BAM input file.
        out1 (file): Annotated output fastq file.
    """

    # Walk the file and create a new annotated file
    while True:
        line1 = in1.readline()
        if not line1:
            # EOF
            break

        parts1 = line1.split()
        name1, seq1, qual1 = parts1[0], parts1[9], parts1[10]

        name1 = '@' + name1

        clip_len1, umi1 = fp_extract_umi(seq1)
        umi_anno = umi1

        name1_anno = "{}{}{}".format(name1, DELIM_ANNO, umi_anno)

        out1.write("{}\n{}\n+\n{}\n".format(name1_anno, seq1[clip_len1:],
            qual1[clip_len1:]))

def create_annotated_files_from_bam(fp_extract_umis, in1, out1, out2):
    """Using a paired-end BAM file as input, create paired FASTQ output files
    with read name annotated with UMI.

    Args:
        fp_extract_umis (function): A function used to extract the UMIs.
        in1 (file): Paired-end BAM input file.
        out1 (file): Read1 annotated output fastq file.
        out2 (file): Read2 annotated output fastq file.
    """

    # Walk the file and create a new annotated file
    while True:
        line1 = in1.readline()
        line2 = in1.readline()
        if not line1:
            # EOF
            break

        parts1 = line1.split()
        parts2 = line2.split()
        name1, seq1, qual1 = parts1[0], parts1[9], parts1[10]
        name2, seq2, qual2 = parts2[0], parts2[9], parts2[10]

        name1 = '@' + name1
        name2 = '@' + name2

        clip_len1, clip_len2, umi1, umi2 = fp_extract_umis(seq1, seq2)
        umis_anno = DELIM_ANNO_READ_PAIR.join([umi1, umi2])

        # Confirm that the file has been sorted!!!
        if name1 != name2:
            raise CannotContinueException(
                     """Expecting paired-end BAM file, but it does not appear
                     to be sorted by name.""")

        # Some datasets have a '/1' and '/2' at end of R1 and R2 read names
        # respectively.
        if name1[-2:] == '/1':
            neg_index = -2
            name = name1[:-2]
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umis_anno)
            name1_anno = "{}/1".format(name_anno)
            name2_anno = "{}/2".format(name_anno)
        else:
            neg_index = 0
            name1_anno = "{}{}{}".format(name1, DELIM_ANNO, umis_anno)
            name2_anno = name1_anno

        # Confirm names are same.
        if name1[:neg_index] != name2[:neg_index]:
            raise ParseException(
                    """Mismatched read names: {}, {}""".format(name1, name2))

        out1.write("{}\n{}\n+\n{}\n".format(name1_anno, seq1[clip_len1:],
            qual1[clip_len1:]))
        out2.write("{}\n{}\n+\n{}\n".format(name2_anno, seq2[clip_len2:],
            qual2[clip_len2:]))

def create_annotated_files_from_fastq(fp_extract_umis, in1, in2, out1, out2,
        has_index):
    """Using paired FASTQ files as input, create paired FASTQ output files with
    read name annotated with UMI.

    Args:
        fp_extract_umis (function): A function used to extract the UMIs.
        in1 (file): Read1 input fastq file.
        in2 (file): Read2 input fastq file.
        out1 (file): Read1 annotated output fastq file.
        out2 (file): Read2 annotated output fastq file.
        has_index (bool): Whether or not these FASTQ files have the index
            string (e.g. 'read_id 1:N:0:ATCACGTT')
    """

    # Walk the file and create a new annotated file
    while True:
        name1, seq1, junk, qual1 = \
                (in1.readline().rstrip() for i in range(4))
        name2, seq2, junk, qual2 = \
                (in2.readline().rstrip() for i in range(4))

        if not name1:
            # EOF
            break

        clip_len1, clip_len2, umi1, umi2 = fp_extract_umis(seq1, seq2)
        umis_anno = DELIM_ANNO_READ_PAIR.join([umi1, umi2])

        if has_index:
            name1, index_str1 = name1.split()
            name2, index_str2 = name2.split()

        if name1[-2:] == '/1':
            # Some datasets have a '/1' and '/2' at end of R1 and R2 read names
            # respectively.
            neg_index = -2
            name = name1[:-2]
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umis_anno)
            record1 = "{}/1\n{}\n+\n{}\n".format(name_anno, seq1[clip_len1:],
                    qual1[clip_len1:])
            record2 = "{}/2\n{}\n+\n{}\n".format(name_anno, seq2[clip_len2:],
                    qual2[clip_len2:])
        elif has_index:
            # Some reads have the index included.
            neg_index = 0
            name = name1
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umis_anno)
            record1 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str1,
                    seq1[clip_len1:], qual1[clip_len1:])
            record2 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str2,
                    seq2[clip_len2:], qual2[clip_len2:])
        else:
            # Some reads have neither the index nor the /1, /2
            neg_index = 0
            name = name1
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umis_anno)
            record1 = "{}\n{}\n+\n{}\n".format(name_anno, seq1[clip_len1:],
                    qual1[clip_len1:])
            record2 = "{}\n{}\n+\n{}\n".format(name_anno, seq2[clip_len2:],
                    qual2[clip_len2:])

        # Confirm names are same.
        if name1[:neg_index] != name2[:neg_index]:
            raise ParseException(
                    """Mismatched read names: {}, {}""".format(name1, name2))

        out1.write(record1)
        out2.write(record2)

def create_annotated_file_from_fastq(fp_extract_umi, in1, out1, has_index):
    """Using single-end FASTQ file as input, create single-end FASTQ output
    file with read name annotated with UMI.

    Args:
        fp_extract_umis (function): A function used to extract the UMIs.
        in1 (file): Input fastq file.
        out1 (file): Annotated output fastq file.
        has_index (bool): Whether or not these FASTQ files have the index
            string (e.g. 'read_id 1:N:0:ATCACGTT')
    """

    # Walk the file and create a new annotated file
    while True:
        name1, seq1, junk, qual1 = \
                (in1.readline().rstrip() for i in range(4))

        if not name1:
            # EOF
            break

        clip_len1, umi1 = fp_extract_umi(seq1)
        umi_anno = umi1

        if has_index:
            name1, index_str1 = name1.split()

        if has_index:
            # Some reads have the index included.
            name = name1
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umi_anno)
            record1 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str1,
                    seq1[clip_len1:], qual1[clip_len1:])
        else:
            # For reads that don't have an index.
            name = name1
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umi_anno)
            record1 = "{}\n{}\n+\n{}\n".format(name_anno, seq1[clip_len1:],
                    qual1[clip_len1:])

        out1.write(record1)

def extract_single_umi_bioo(seq1):
    """Extract the Bioo UMI from a single end read.

    Args:
        seq1 (str): The full read1 (with UMI).
    Returns:
        (int, str): A 2-tuple, the int representing the amount
            to clip from the read, the str is the UMI of the read.
    """
    umi_len = len(UMIS_BIOO[0])
    # The Bioo kit uses a 1nt 'T' overhang for ligation.
    clip_len = umi_len + 1

    umi1 = seq1[:umi_len]

    return (clip_len, umi1)

def extract_paired_umis_bioo(seq1, seq2):
    """Extract the Bioo UMIs from a paired read.

    Args:
        seq1 (str): The full read1 (with UMI).
        seq2 (str): The full read2 (with UMI).
    Returns:
        (int, int, str, str): A 4-tuple, first two ints representing the amount
            to clip from the two reads respectively, second two strs are the
            UMIs of each read respectively.
    """
    umi_len = len(UMIS_BIOO[0])
    # The Bioo kit uses a 1nt 'T' overhang for ligation.
    clip_len = umi_len + 1
    umi1 = seq1[:umi_len]
    umi2 = seq2[:umi_len]

    return (clip_len, clip_len, umi1, umi2)

def parse_args(args):
    """Parse the command line arguments. """

    # Paired or single end? FASTQ or BAM?
    if args['<in2.fastq>']:
        # mode = FASTQ, PE
        paired = True
        filetype = 'FASTQ'
        # Convert ~ to real path
        args['<in1.fastq>'] = os.path.expanduser(args['<in1.fastq>'])
        args['<in2.fastq>'] = os.path.expanduser(args['<in2.fastq>'])
        input_files = [args['<in1.fastq>'], args['<in2.fastq>']]
    else:
        # Convert ~ to real path
        args['<input.fastq>'] = os.path.expanduser(args['<input.fastq>'])

        # Note: If you write the following for docopt:
        #   dupliganger remove-umi [options] <input.fastq>
        #   dupliganger remove-umi [options] <input.bam>
        # then it will always populate <input.fastq> and never populate
        # <input.bam>, hence the somewhat confusing names going on down
        # below...
        if is_bam(args['<input.fastq>']):
            # It is a bam, so hack docopt a bit
            args['<input.bam>'] = args['<input.fastq>']
            args['<input.fastq>'] = None
            paired = True if is_paired_bam(args['<input.bam>']) else False
            filetype = 'BAM'
            input_files = [args['<input.bam>']]
        else:
            # mode = FASTQ, SR
            paired = False
            filetype = 'FASTQ'
            input_files = [args['<input.fastq>']]

    # What fp_extract_umi to use?
    kit = args['--kit']
    if kit == KIT_BIOO:
        if paired:
            fp_extract_umi = extract_paired_umis_bioo
        else:
            fp_extract_umi = extract_single_umi_bioo
    else:
        raise CannotContinueException(
                """Kit {} is not supported.""".format(kit))

    # Figure out which function to use to write to output file.
    num_threads = int(args['--threads'])
    compress = args['--compress']
    if num_threads > 1 and which('pigz') and compress:
        # return a partial for pigzwrite
        # TODO: Maybe alter this to num_threads/2 if --paired-end?
        fp_write = functools.partial(pigzwrite, num_threads)
    elif which('gzip') and compress:
        # return a partial for gzwrite
        fp_write = gzwrite
    else:
        fp_write = functools.partial(open, mode = 'w')

    # Return an appropriate function pointer for annotation.
    if filetype == 'FASTQ':
        if paired:
            fp_anno = create_annotated_files_from_fastq
        else:
            fp_anno = create_annotated_file_from_fastq
    elif filetype == 'BAM':
        if paired:
            fp_anno = create_annotated_files_from_bam
        else:
            fp_anno = create_annotated_file_from_bam
    else:
        raise ControlFlowException(
                """ERR213: Not possible to be here.""")

    outdir = args_to_out_dir(args)

    if args['--force-paired'] and not paired:
        sys.stderr.write(
                "WARNING: Passed --force-paired but {} appears not to be "
                "paired-end.\n")
    force_paired = args['--force-paired']

    return (fp_extract_umi, fp_anno, fp_write, outdir, compress, force_paired,
            input_files)

def run(fp_extract_umi, fp_anno, fp_write, outdir, compress, force_paired,
        input_files):
    """Start the run.

    Args:
        fp_extract_umi (function): Function extract UMIs from single/paired
            reads, also returns the length(s) to clip.
        fp_anno (Function): Function to be used to parse the FASTQ or BAM file(s).
        fp_write (Function): Function to be used to write output file(s).
        outdir (str): Output directory for results
        compress (bool): Whether or not to compress the output.
        force_paired (bool): Whether user wants to force paired-end, even if
            if we didn't detect it.
        input_files ([str]): Array of input files to be parsed.
    """

    if fp_anno == create_annotated_files_from_bam or force_paired:
        # BAM, paired-end
        infile1 = input_files[0]
        out1, out2 = filename_in_bam_to_out_fqgz(infile1,
                SUFFIX_REMOVE_UMI, compress, True, outdir)
        out_files = [out1, out2]
        tmp_out1, tmp_out2 = tmpf_start(out1, out2)

        with bamopen(infile1) as in1, \
                fp_write(tmp_out1) as out1, \
                fp_write(tmp_out2) as out2:
            fp_anno(fp_extract_umi, in1, out1, out2)
        tmpf_finish(tmp_out1, tmp_out2)

    elif fp_anno == create_annotated_file_from_bam:
        # BAM, single-end
        infile1 = input_files[0]
        out1 = filename_in_bam_to_out_fqgz(infile1, SUFFIX_REMOVE_UMI,
                compress, False, outdir)[0]
        out_files = [out1]
        tmp_out1 = tmpf_start(out1)[0]

        with bamopen(infile1) as in1, \
                fp_write(tmp_out1) as out1:
            fp_anno(fp_extract_umi, in1, out1)
        tmpf_finish(tmp_out1)

    else:

        # Some datasets have look like this:
        #       @NS500451:139:H5TV5AFXX:1:11101:3928:1111 1:N:0:ATCACGTT
        # Others like this:
        #       @NS500451:139:H5TV5AFXX:1:11101:3928:1111
        # Detect.
        if is_gzipped(input_files[0]):
            with gzip.open(input_files[0], mode='rt') as in1:
                first_line = in1.readline()
        else:
            with io.open(input_files[0], mode='r', encoding='latin-1') as in1:
                first_line = in1.readline()
        has_index = True if len(first_line.split()) > 1 else False

        # FASTQ
        if len(input_files) == 2:
            # FASTQ, paired-end
            infile1, infile2 = input_files
            out1 = filename_in_to_out_fqgz(infile1, SUFFIX_REMOVE_UMI, compress,
                    outdir)
            out2 = filename_in_to_out_fqgz(infile2, SUFFIX_REMOVE_UMI, compress,
                    outdir)
            out_files = [out1, out2]
            tmp_out1, tmp_out2 = tmpf_start(out1, out2)

            with pgopen(1, infile1) as in1, \
                    pgopen(1, infile2) as in2, \
                    fp_write(tmp_out1) as out1, \
                    fp_write(tmp_out2) as out2:
                fp_anno(fp_extract_umi, in1, in2, out1, out2, has_index)
            tmpf_finish(tmp_out1, tmp_out2)

        elif len(input_files) == 1:
            # FASTQ, single-end
            infile1 = input_files[0]
            out1 = filename_in_to_out_fqgz(infile1, SUFFIX_REMOVE_UMI, compress,
                    outdir)
            out_files = [out1]
            tmp_out = tmpf_start(out1)[0]

            with pgopen(1, infile1) as in1, \
                    fp_write(tmp_out) as out1:
                fp_anno(fp_extract_umi, in1, out1, has_index)
            tmpf_finish(tmp_out)

        else:
            raise ControlFlowException(
                    """ERR911: Not possible to be here.""")

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

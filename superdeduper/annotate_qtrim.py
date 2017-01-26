# Copyright (C) 2014, 2015  Jason Sydes
#
# This file is part of SuperDeDuper
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the License with this program.
#
# Written by Jason Sydes

"""Annotate quality trimmed files with number of 5' and 3' NTs trimmed.

'annotate-qtrim' uses the 'trimlog' produced by Trimmomatic to annotate.

Usage:
    superdeduper annotate-qtrim [options] <input.fastq>
    superdeduper annotate-qtrim [options] <in1.fastq> <in2.fastq>

Note:
    SuperDeDuper supports (and autodetects) input FASTQ files that are gzipped.

Options:
    -h, --help
    -v, --verbose         Be verbose.
    -l TRIMLOG            Optionally specify trimlog.
    -o OUT_DIR            Place results in directory OUT_DIR.
    --compress            Compress (gzip) output files.
    -t N, --threads N     EXPERIMENTAL: If pigz is installed and --threads is
                          specified, output FASTQ files will be compressed with
                          pigz -p <n>; otherwise, they will be left
                          uncompressed (as it simply takes too long to compress
                          with just gzip) [default: 1].
"""

###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from builtins import range

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.exceptions import *
from superdeduper.common import (pgopen, tmpf_start, tmpf_finish,
        is_gzipped, filename_in_to_out_fqgz, pe_log_filename, se_log_filename,
        args_to_out_dir)

## Other imports
from docopt import docopt

# For converting ~ to full path
import os

# For shell-like "which()"
try:
    from shutil import which
except ImportError:
    from whichcraft import which

# For function partials
import functools

# For inspecting gzipped files
import gzip


#################
### Constants ###
#################

#################
### Functions ###
#################

def create_annotated_files(in1, in2, trim_log, out1, out2, has_index):
    """Creates paired-end files with read names annotated with amount of 5'-trimming.

    Example:
        "ReadName-ACGT|GGCC" -> "ReadName-ACGT|GGCC;1^5"

    Args:
        in1 (file): Read1 fastq input filehandle.
        in2 (file): Read2 fastq input filehandle.
        trim_log (file): Trimmomatic trim log.
        out1 (file): Read1 annotated fastq output filehandle.
        out2 (file): Read2 annotated fastq output filehandle.
        has_index (bool): Whether or not these FASTQ files have the index
            string (e.g. 'read_id 1:N:0:ATCACGTT')
    """
    eof = False
    while True:
        name1, seq1, _, qual1 = \
                (in1.readline().rstrip() for i in range(4))
        name2, seq2, _, qual2 = \
                (in2.readline().rstrip() for i in range(4))

        if not name1 or not name2:
            break

        if has_index:
            name1, index_str1 = name1.split()
            name2, index_str2 = name2.split()

        # examples:
        # D00597:180:C7NMDANXX:6:1101:1184:35164-ACGAAGGT|GAGAAGAG/1 110 3 113 4
        # D00597:180:C7NMDANXX:6:1101:1184:35164-ACGAAGGT|GAGAAGAG/2 117 0 117 0

        tname1 = None
        tname2 = None
        while (tname1 != name1 or tname2 != name2):

            p1 = trim_log.readline().split()
            p2 = trim_log.readline().split()

            if len(p1) == 0 or len(p2) == 0:
                eof = True
                break

            if has_index:
                tname1, _, _, trimmed1_5p, last_base_pos1, trimmed1_3p = p1
                tname2, _, _, trimmed2_5p, last_base_pos2, trimmed2_3p = p2
            else:
                tname1, _, trimmed1_5p, last_base_pos1, trimmed1_3p = p1
                tname2, _, trimmed2_5p, last_base_pos2, trimmed2_3p = p2

            # prefix '@' to match name[12]
            tname1 = '@' + tname1
            tname2 = '@' + tname2

        if eof:
            # EOF
            break

        assert (tname1 == name1)
        assert (tname2 == name2)

        # e.g. "1^5"
        trimmed = "{}{}{}".format(trimmed1_5p, DELIM_ANNO_READ_PAIR,
                trimmed2_5p)

        if name1[-2:] == '/1':
            # Some datasets have a '/1' and '/2' at end of R1 and R2 read names
            # respectively.
            name = name1[:-2]
            # e.g. "ReadName-ACGT,AATT|GGCC;1^5"
            name_anno = DELIM_ANNO_TYPE.join((name, trimmed))
            record1 = "{}/1\n{}\n+\n{}\n".format(name_anno, seq1, qual1)
            record2 = "{}/2\n{}\n+\n{}\n".format(name_anno, seq2, qual2)
        elif has_index:
            # Some reads have the index included.
            name = name1
            name_anno = DELIM_ANNO_TYPE.join((name, trimmed))
            record1 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str1, seq1, qual1)
            record2 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str2, seq2, qual2)
        else:
            # Some reads have neither the index nor the /1, /2
            name = name1
            name_anno = DELIM_ANNO_TYPE.join((name, trimmed))
            record1 = "{}\n{}\n+\n{}\n".format(name_anno, seq1, qual1)
            record2 = "{}\n{}\n+\n{}\n".format(name_anno, seq2, qual2)

        # Write the files
        out1.write(record1)
        out2.write(record2)

def create_annotated_file(in1, trim_log, out1, has_index):
    """Creates single-end FASTQ file with read names annotated with amount of 5'-trimming.

    Example:
        "ReadName-ACGT" -> "ReadName-ACGT;1"

    Args:
        in1 (file): FASTQ input filehandle.
        trim_log (file): Trimmomatic trim log.
        out1 (file): Annotated fastq output filehandle.
        has_index (bool): Whether or not this FASTQ file has the index
            string (e.g. 'read_id 1:N:0:ATCACGTT')
    """
    eof = False
    while True:
        name1, seq1, _, qual1 = \
                (in1.readline().rstrip() for i in range(4))

        if not name1:
            break

        if has_index:
            name1, index_str1 = name1.split()

        # examples:
        # D00597:180:C7NMDANXX:6:1101:1184:35164-ACGAAGGT 110 3 113 4

        tname1 = None
        while (tname1 != name1):
            p1 = trim_log.readline().split()

            if len(p1) == 0:
                eof = True
                break

            if has_index:
                tname1, _, _, trimmed1_5p, last_base_pos1, trimmed1_3p = p1
            else:
                tname1, _, trimmed1_5p, last_base_pos1, trimmed1_3p = p1

            # prefix '@' to match name1
            tname1 = '@' + tname1

        if eof:
            # EOF
            break

        assert (tname1 == name1)

        # e.g. "1"
        trimmed = "{}".format(trimmed1_5p)

        if has_index:
            # Some reads have the index included.
            name = name1
            name_anno = DELIM_ANNO_TYPE.join((name, trimmed))
            record1 = "{} {}\n{}\n+\n{}\n".format(name_anno, index_str1, seq1, qual1)
        else:
            # Some reads have neither the index nor the /1, /2
            name = name1
            name_anno = DELIM_ANNO_TYPE.join((name, trimmed))
            record1 = "{}\n{}\n+\n{}\n".format(name_anno, seq1, qual1)

        # Write the files
        out1.write(record1)

def parse_args(args):
    """Parse the command line arguments."""

    # Convert ~ to real path (strip silly leading './' too)
    if args['<in2.fastq>']:
        # PE mode
        in1 = os.path.expanduser(args['<in1.fastq>'])
        in2 = os.path.expanduser(args['<in2.fastq>'])
        input_files = (in1, in2)
    else:
        fin = os.path.expanduser(args['<input.fastq>'])
        input_files = (fin, )

    # Figure out which function to use to write to output file.
    compress = args['--compress']
    num_threads = int(args['--threads'])
    if num_threads > 1 and which('pigz') and compress:
        # return a partial for pigzwrite
        write_func = functools.partial(pigzwrite, num_threads)
    else:
        write_func = functools.partial(open, mode = 'w')

    outdir = args_to_out_dir(args)

    # optional trimlog
    opt_trimlog = args['-l'] if args['-l'] else None

    return (write_func, outdir, compress, opt_trimlog, input_files)

def run(write_func, outdir, compress, opt_trimlog, input_files):
    """Start the run.

    Args:
        outdir (str): Output directory for results
        compress (bool): Whether or not to compress the output.
        input_files ([str]): Input files.
    """

    # Some fastq files have an index read in them. Detect.
    if is_gzipped(input_files[0]):
        with gzip.open(input_files[0], 'rb') as in1:
            first_line = in1.readline()
    else:
        with open(input_files[0], 'r') as in1:
            first_line = in1.readline()
    has_index = True if len(first_line.split()) > 1 else False

    if len(input_files) == 2:
        in1, in2 = input_files
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_ANNOTATE_QTRIM, compress,
                outdir)
        out2 = filename_in_to_out_fqgz(in2, SUFFIX_ANNOTATE_QTRIM, compress,
                outdir)
        out_files = [out1, out2]

        if opt_trimlog is not None:
            trim_log = opt_trimlog
        else:
            qtrim_out2_file = out2.replace(SUFFIX_QTRIM + '.', '')
            trim_log = pe_log_filename(SUFFIX_QTRIM, in2, 'trimlog')

        tmp_out1, tmp_out2 = tmpf_start(out1, out2)

        with    pgopen(1, in1) as fin1, \
                pgopen(1, in2) as fin2, \
                pgopen(1, trim_log) as ftrim_log, \
                write_func(tmp_out1) as fout1, \
                write_func(tmp_out2) as fout2:
            create_annotated_files(fin1, fin2, ftrim_log, fout1, fout2, has_index)

        tmpf_finish(tmp_out1, tmp_out2)

    elif len(input_files) == 1:
        in1 = input_files[0]
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_ANNOTATE_QTRIM, compress,
                outdir)
        out_files = [out1]

        if opt_trimlog is not None:
            trim_log = opt_trimlog
        else:
            qtrim_out_file = out1.replace(SUFFIX_QTRIM + '.', '')
            trim_log = se_log_filename(SUFFIX_QTRIM, in1, 'trimlog')

        tmp_out1 = tmpf_start(out1)[0]
        with    pgopen(1, in1) as fin1, \
                pgopen(1, trim_log) as ftrim_log, \
                write_func(tmp_out1) as fout1:
            create_annotated_file(fin1, ftrim_log, fout1, has_index)
        tmpf_finish(tmp_out1)

    else:
        raise ControlFlowException("""ERR911: Not possible to be here.""")

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

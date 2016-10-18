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

"""Annotates read names with UMIs and clips inline UMIs if needed.

Usage:
    superdeduper remove-umi [options] <input.fastq>
    superdeduper remove-umi [options] <in1.fastq> <in2.fastq>


Note:
    SuperDeDuper supports (and autodetects) input FASTQ files that are gzipped.

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
                          with just gzip).
"""

###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# version
from superdeduper._version import __version__

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.common import (pgopen, gzwrite, pigzwrite, tmpf_start, tmpf_finish,
        filename_in_to_out_fqgz, args_to_out_dir)

## Other imports
from docopt import docopt

# For filename fixing
import os

# For writing gzipped files
import gzip

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

def create_annotated_files(fp_extract_umis, in1, in2, out1, out2):
    """Create a FASTQ file, with read name annotated with UMI, paired-end
    version.

    Args:
        fp_extract_umis (function): A function used to extract the UMIs.
        in1 (file): Read1 input fastq file.
        in2 (file): Read2 input fastq file.
        out1 (file): Read1 annotated output fastq file.
        out2 (file): Read2 annotated output fastq file.
    """

    # Walk the file and create a new annotated file
    while True:
        name1, seq1, junk, qual1 = \
                (in1.readline().rstrip() for i in xrange(4))
        name2, seq2, junk, qual2 = \
                (in2.readline().rstrip() for i in xrange(4))

        if not name1:
            # EOF
            break

        clip_len1, clip_len2, umi1, umi2 = fp_extract_umis(seq1, seq2)
        umis_anno = DELIM_ANNO_READ_PAIR.join([umi1, umi2])

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
            raise ParseException, \
                    """Mismatched read names: {}, {}""".format(name1,
                            name2)

        out1.write("{}\n{}\n+\n{}\n".format(name1_anno, seq1[clip_len1:],
            qual1[clip_len1:]))
        out2.write("{}\n{}\n+\n{}\n".format(name2_anno, seq2[clip_len2:],
            qual2[clip_len2:]))

def create_annotated_file(fp_extract_umi, in1, out1):
    """Create a FASTQ file, with read name annotated with UMI, single-end
    version.

    Args:
        fp_extract_umis (function): A function used to extract the UMIs.
        in1 (file): Input fastq file.
        out1 (file): Annotated output fastq file.
    """

    # Walk the file and create a new annotated file
    while True:
        name1, seq1, junk, qual1 = \
                (in1.readline().rstrip() for i in xrange(4))

        if not name1:
            # EOF
            break

        clip_len1, umi1 = fp_extract_umi(seq1)
        umi_anno = umi1

        # Some datasets have a '/1' at end of read names.
        if name1[-2:] == '/1':
            name = name1[:-2]
            name_anno = "{}{}{}".format(name, DELIM_ANNO, umi_anno)
            name1_anno = "{}/1".format(name_anno)
        else:
            name1_anno = "{}{}{}".format(name1, DELIM_ANNO, umis_anno)

        out1.write("{}\n{}\n+\n{}\n".format(name1_anno, seq1[clip_len1:],
            qual1[clip_len1:]))

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

def parse_args():
    """Parse the command line arguments. """
    args = docopt(__doc__)

    paired = True if args['<in2.fastq>'] else False

    # Convert ~ to real path
    if args['<in2.fastq>']:
        args['<in1.fastq>'] = os.path.expanduser(args['<in1.fastq>'])
        args['<in2.fastq>'] = os.path.expanduser(args['<in2.fastq>'])
    else:
        args['<input.fastq>'] = os.path.expanduser(args['<input.fastq>'])

    # What fp_extract_umi to use?
    kit = args['--kit']
    if kit == KIT_BIOO:
        if paired:
            fp_extract_umi = extract_paired_umis_bioo
        else:
            fp_extract_umi = extract_single_umi_bioo
    else:
        raise CannotContinueException, \
                """Kit {} is not supported.""".format(kit)

    # Figure out which function to use to write to output file.
    num_threads = args['--threads']
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
    if paired:
        input_files = [args['<in1.fastq>'], args['<in2.fastq>']]
        fp_anno = create_annotated_files
    else:
        input_files = [args['<input.fastq>']]
        fp_anno = create_annotated_file

    outdir = args_to_out_dir(args)

    return (fp_extract_umi, fp_anno, fp_write, outdir, compress, input_files)

def run(fp_extract_umi, fp_anno, fp_write, outdir, compress, input_files):
    """Start the run.

    Args:
        fp_extract_umi (function): Function extract UMIs from single/paired
            reads, also returns the length(s) to clip.
        fp_anno (Function): Function to be used to parse the fastq file(s).
        fp_write (Function): Function to be used to write output file(s).
        outdir (str): Output directory for results
        compress (bool): Whether or not to compress the output.
        input_files ([str]): Array of input fastq files to be parsed.
    """

    if len(input_files) == 2:
        infile1, infile2 = input_files
        out1 = filename_in_to_out_fqgz(infile1, SUFFIX_REMOVE_UMI, compress,
                outdir)
        out2 = filename_in_to_out_fqgz(infile2, SUFFIX_REMOVE_UMI, compress,
                outdir)
        tmp_out1, tmp_out2 = tmpf_start(out1, out2)

        with pgopen(1, infile1) as in1, \
                pgopen(1, infile2) as in2, \
                fp_write(tmp_out1) as out1, \
                fp_write(tmp_out2) as out2:
            fp_anno(fp_extract_umi, in1, in2, out1, out2)
        tmpf_finish(tmp_out1, tmp_out2)

    elif len(input_files) == 1:
        infile = input_files[0]
        out = filename_in_to_out_fqgz(infile, SUFFIX_REMOVE_UMI, compress,
                outdir)
        tmp_out = tmpf_start(out)[0]

        with pgopen(1, infile) as in1, \
                fp_write(tmp_out) as out1:
            fp_anno(fp_extract_umi, int1, out1)
        tmpf_finish(tmp_out)
    else:
        raise ControlFlowException, \
                """ERR911: Not possible to be here."""


###############
### Classes ###
###############


############
### Main ###
############

def main():
    args = docopt(__doc__)
    run(*parse_args())

# vim: softtabstop=4:shiftwidth=4:expandtab

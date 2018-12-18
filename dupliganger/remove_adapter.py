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

"""Remove adapters.  This is simply a 'Cutadapt' wrapper.

Usage:
    dupliganger remove-adapter [options] <input.fastq>
    dupliganger remove-adapter [options] <in1.fastq> <in2.fastq>


Note:
    Dupligänger supports (and autodetects) input FASTQ files that are gzipped.

Options:
    -h, --help
    -v, --verbose   Be verbose
    --compress      Compress output.
    -o OUT_DIR      Place results in directory OUT_DIR.

    -C S, --cutadapt S  Pass 'S' as arguments to Cutadapt. Don't forget to put quotes
                        around S if passing in more than one argument.
                        [default: '-n 3 -O 1 -m 30']
    -1 A, --adapter1    First (Illumina) adapter [default: AGATCGGAAGAGC]
    -2 A, --adapter2    Second (Illumina) adapter [default: AGATCGGAAGAGC]

"""


###############
### Imports ###
###############

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object

# Dupligänger imports
from dupliganger.constants import *
from dupliganger.exceptions import *
from dupliganger.common import (pgopen, tmpf_start, tmpf_finish,
        filename_in_to_out_fqgz, pe_log_filename, se_log_filename,
        args_to_out_dir)

## Other imports
from docopt import docopt

# For converting ~ to full path
import os

# # For shell-like "which()"
try:
    from shutil import which
except ImportError:
    from whichcraft import which

# For external command execution
import subprocess, shlex


#################
### Constants ###
#################


#################
### Functions ###
#################

def pe_remove_adapters(in1, in2, out1, out2, short1, short2, out_log, adapter1,
        adapter2, cutadapt_args):
    """Remove adapter, paired-end version.

    Args:
        in1 (file): Read1 fastq input file.
        in2 (file): Read1 fastq input file.
        out1 (file): Read1 fastq adapter removed output file.
        out2 (file): Read2 fastq adapter removed output file.
        short1 (file): Read1 cutadapt --too-short-output file.
        short2 (file): Read2 cutadapt --too-short-paired-output file.
        out_log (str): Stdout/stderr of cutadapt execution.
        adapter1 (str): Illumina adapter1.
        adapter2 (str): Illumina adapter2.
        cutadapt_args (str): Arguments to pass to cutadapt.
    """

    adapters = "-a {} -A {}".format(adapter1, adapter2)
    ins = "{} {}".format(in1, in2)
    outs = "-o {} -p {}".format(out1, out2)
    too_short = "--too-short-output={} --too-short-paired-output={}".format(
            short1, short2)

    cmd = "cutadapt {} {} {} {} {}".format(cutadapt_args, adapters, ins, outs,
            too_short)
    print("Running:\n\t{}".format(cmd))
    cmd = shlex.split(cmd)

    with open(out_log, 'w') as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, bufsize=-1)
        retval = p.wait()
    if retval > 0:
        raise ExecutionException(
                """Failure to execute properly. See {}""".format(out_log))

def se_remove_adapter(in1, out1, short1, out_log, adapter1, cutadapt_args):
    """Remove adapter, single-end version.

    Args:
        in1 (file): fastq input file.
        out1 (file): fastq adapter removed output file.
        short1 (file): cutadapt --too-short-output file.
        out_log (str): Stdout/stderr of cutadapt execution.
        adapter1 (str): Illumina adapter1.
        cutadapt_args (str): Arguments to pass to cutadapt.
    """

    adapters = "-a {}".format(adapter1)
    ins = "{}".format(in1)
    outs = "-o {}".format(out1)
    too_short = "--too-short-output={}".format(short1)

    cmd = "cutadapt {} {} {} {} {}".format(cutadapt_args, adapters, ins, outs,
            too_short)
    print("Running:\n\t{}".format(cmd))
    cmd = shlex.split(cmd)

    with open(out_log, 'w') as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, bufsize=-1)
        retval = p.wait()
    if retval > 0:
        raise ExecutionException(
                """Failure to execute properly. See {}""".format(out_log))

def parse_args(args):
    """Parse the command line arguments."""
    adapters = []

    # Convert ~ to real path
    if args['<in2.fastq>']:
        in1 = os.path.expanduser(args['<in1.fastq>'])
        in2 = os.path.expanduser(args['<in2.fastq>'])
        input_files = [in1, in2]
        if not args['--adapter1'] or not args['--adapter2']:
            raise ArgumentException(
                    """Error:

                    --adapter1 and --adapter2 are required if running in
                    paired-end mode (i.e. when you give two FASTQ files).

                    """)
        adapters = [args['--adapter1'], args['--adapter2']]
    else:
        input_files = [os.path.expanduser(args['<input.fastq>'])]
        adapters = [args['--adapter1']]
        # Uncomment if we ever remove the default from the --apapter arguments
        # if args['--adapter2']:
        #     raise ArgumentException(
        #             """Error:

        #             --adapter2 was given (suggesting you wanted paired-end
        #             adapter removal), but only one FASTQ file was given.

        #             """)

    outdir = args_to_out_dir(args)

    cutadapt_args = args['--cutadapt'].strip("'").strip('"').strip("'")

    # compress output?
    compress = args['--compress']
    return (compress, outdir, cutadapt_args, adapters, input_files)

def run(compress, outdir, cutadapt_args, adapters, input_files):
    """Start the run.

    Args:
        compress (bool): Whether or not to compress output.
        outdir (str): Output directory for results
        cutadapt_args (str): Arguments to pass to cutadapt.
        adapters ([str]): List of Illumina adapters to cutadapt.
        input_files ([str]): Array of input fastq file(s) to be parsed.
    Returns:
        out_files ([str]): Array of output fastq file(s).

    """
    if not which('cutadapt'):
        raise PrerequisitesException(
                """Cannot find 'cutadapt'.  Install with:

                pip install cutadapt

                """)

    if len(input_files) == 2:
        in1, in2 = input_files
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_REMOVE_ADAPTER, compress,
                outdir)
        out2 = filename_in_to_out_fqgz(in2, SUFFIX_REMOVE_ADAPTER, compress,
                outdir)
        out_files = [out1, out2]
        adapter1, adapter2 = adapters
        out_log = pe_log_filename(SUFFIX_REMOVE_ADAPTER, out2)
        # i.e. for those that are too short...
        short_out1 = filename_in_to_out_fqgz(out1,
                SUFFIX_REMOVE_ADAPTER_TOO_SHORT, compress, outdir)
        short_out2 = filename_in_to_out_fqgz(out2,
                SUFFIX_REMOVE_ADAPTER_TOO_SHORT, compress, outdir)

        tmp_out1, tmp_out2, tmp_short_out1, tmp_short_out2 = tmpf_start(out1,
                out2, short_out1, short_out2)

        pe_remove_adapters(in1, in2, tmp_out1, tmp_out2, tmp_short_out1,
                tmp_short_out2, out_log, adapter1, adapter2, cutadapt_args)
        tmpf_finish(tmp_out1, tmp_out2, tmp_short_out1, tmp_short_out2)

    elif len(input_files) == 1:
        in1 = input_files[0]
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_REMOVE_ADAPTER, compress,
                outdir)
        out_files = [out1]
        adapter1 = adapters[0]
        out_log = se_log_filename(SUFFIX_REMOVE_ADAPTER, out1)
        # i.e. for those that are too short...
        short_out1 = filename_in_to_out_fqgz(out1,
                SUFFIX_REMOVE_ADAPTER_TOO_SHORT, compress, outdir)

        tmp_out1, tmp_short_out1 = tmpf_start(out1, short_out1)

        se_remove_adapter(in1, tmp_out1, tmp_short_out1, out_log, adapter1,
                cutadapt_args)
        tmpf_finish(tmp_out1, tmp_short_out1)

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

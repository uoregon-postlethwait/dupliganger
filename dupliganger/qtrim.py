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

"""Quality trim reads.  This is a 'Trimmomatic' wrapper.

Usage:
    dupliganger qtrim [options] <input.fastq>
    dupliganger qtrim [options] <in1.fastq> <in2.fastq>


Note:
    Dupligänger supports (and autodetects) input FASTQ files that are gzipped.

Options:
    -h, --help
    -v, --verbose           Be verbose.
    -o OUT_DIR              Place results in directory OUT_DIR.
    --compress              Compress (gzip) output files.
    -t N, --threads N       Number of threads to run with [default: 1].
    -T S, --trimmomatic S   Pass 'S' as arguments to Trimmomatic. Don't forget to put quotes
                            around S if passing in more than one argument.
                            [default: 'LEADING:10 TRAILING:10 SLIDINGWINDOW:5:10 MINLEN:30']
    -p P, --phred P         Set P to 33 for phred33 encoded files, or 64 for
                            phred 64 encoded FASTQ files [default: 33].
"""

###############
### Imports ###
###############

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object

# Dupligänger imports
from dupliganger.exceptions import *
from dupliganger.constants import *
from dupliganger.common import (pgopen, tmpf_start, tmpf_finish,
        filename_in_to_out_fqgz, pe_log_filename, se_log_filename,
        args_to_out_dir)

## Other imports
from docopt import docopt

# For converting ~ to full path
import os

# For external command execution
import subprocess, shlex


#################
### Constants ###
#################

FIXME_TRIMMOMATIC_SRC = '~/src/Trimmomatic-0.36/trimmomatic-0.36.jar'

#################
### Functions ###
#################

def qtrim(num_threads, phred, trimmomatic_args, *input_output_files):
    """Quality trim reads with Trimmomatic.

    Args:
        num_threads (int): How many threads to run with.
        phred (int): Phred encoding of fastq file(s). (33 or 64)
        trimmomatic_args (str): Arguments (in string format) to pass to
            Trimmomatic (e.g. TRAILING:10 MINLEN:50).
        input_output_files ([str]): Input and output files.
    """

    threads = "-threads {}".format(num_threads)
    unpaired1 = ''

    if len(input_output_files) == 8:
        in1, in2, out1, out2, unpaired1, unpaired2, out_log, trim_log = \
                input_output_files
        ins = "{} {}".format(in1, in2)
        outs = "{} {} {} {}".format(out1, unpaired1, out2, unpaired2)
        mode = 'PE'
    elif len(input_output_files) == 4:
        in1, out1, out_log, trim_log = input_output_files
        ins = "{}".format(in1)
        outs = "{} {}".format(out1, unpaired1)
        mode = 'SE'
    else:
        raise ControlFlowException("""ERR911: Not possible to be here.""")

    phred = "-phred{}".format(phred)
    trimlog_str = "-trimlog {}".format(trim_log)

    cmd = "java -jar {} {} {} {} {} {} {} {}".format(
            os.path.expanduser(FIXME_TRIMMOMATIC_SRC), mode, threads, phred,
            trimlog_str, ins, outs, trimmomatic_args)

    print("Running:\n\t{}".format(cmd))
    cmd = shlex.split(cmd)

    with open(out_log, 'w') as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, bufsize=-1)
        retval = p.wait()
    if retval > 0:
        raise ExecutionException(
                """Failure to execute properly. See {}""".format(out_log))

def parse_args(args):
    """Parse the command line arguments.
    """

    # Convert ~ to real path, and get input files
    if args['<in2.fastq>']:
        fin1 = os.path.expanduser(args['<in1.fastq>'])
        fin2 = os.path.expanduser(args['<in2.fastq>'])
        input_files = [fin1, fin2]
    else:
        fin = os.path.expanduser(args['<input.fastq>'])
        input_files = [fin]

    num_threads = int(args['--threads'])
    compress = args['--compress']
    outdir = args_to_out_dir(args)

    phred = args['--phred']
    if phred not in ('33', '64'):
        raise CannotContinueException(
                """Phred score {} is not supported.""".format(phred))
    phred = int(phred)

    trimmomatic_args = args['--trimmomatic'].strip("'").strip('"').strip("'")

    return (num_threads, outdir, compress, phred, trimmomatic_args, input_files)

def run(num_threads, outdir, compress, phred, trimmomatic_args, input_files):
    """Start the run.

    Args:
        num_threads (int): How many threads to run with.
        outdir (str): Output directory for results
        compress (bool): Whether or not to compress the output.
        phred (int): Phred encoding of fastq file(s). (33 or 64)
        trimmomatic_args (str): Arguments (in string format) to pass to
            Trimmomatic (e.g. TRAILING:10 MINLEN:50).
        input_files ([str]): Input files.
    """

    if len(input_files) == 2:
        in1, in2 = input_files
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_QTRIM, compress, outdir)
        out2 = filename_in_to_out_fqgz(in2, SUFFIX_QTRIM, compress, outdir)
        out_files = [out1, out2]
        out_log = pe_log_filename(SUFFIX_QTRIM, out2)
        trim_log = pe_log_filename(SUFFIX_QTRIM, out2, 'trimlog')
        # i.e. for those that end up unpaired because partner trimmed too much
        unpaired_out1 = filename_in_to_out_fqgz(out1, SUFFIX_QTRIM_UNPAIRED,
                compress, outdir)
        unpaired_out2 = filename_in_to_out_fqgz(out2, SUFFIX_QTRIM_UNPAIRED,
                compress, outdir)

        tmp_out1, tmp_out2, tmp_unpaired_out1, tmp_unpaired_out2 = tmpf_start(out1,
                out2, unpaired_out1, unpaired_out2)

        qtrim(num_threads, phred, trimmomatic_args, in1, in2, tmp_out1,
                tmp_out2, tmp_unpaired_out1, tmp_unpaired_out2, out_log,
                trim_log)
        tmpf_finish(tmp_out1, tmp_out2, tmp_unpaired_out1, tmp_unpaired_out2)

    elif len(input_files) == 1:
        in1 = input_files[0]
        out1 = filename_in_to_out_fqgz(in1, SUFFIX_QTRIM, compress, outdir)
        out_files = [out1]
        out_log = se_log_filename(SUFFIX_QTRIM, out1)
        trim_log = se_log_filename(SUFFIX_QTRIM, out1, 'trimlog')

        tmp_out1 = tmpf_start(out1)[0]

        qtrim(num_threads, phred, trimmomatic_args, in1, tmp_out1, out_log,
                trim_log)
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

# Copyright (C) 2016 Jason Sydes
#
# This file is part of SuperDeDuper.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the License with this program.
#
# Written by Jason Sydes.

###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# SuperDeDuper imports

## Other imports

import pytest
import os
import sys
import shutil

#################
### Constants ###
#################

LAST_RUN_DIR            = 'last_run'
EXPECTED_OUT_DIR        = 'eout'
BASE_FILES_DIR          = 'superdeduper/test/files'
                          # e.g. 'superdeduper/test/files/last_run')
BASE_OUTFILE_DIR        = os.path.join(BASE_FILES_DIR, LAST_RUN_DIR)


#################
### Functions ###
#################

@pytest.fixture(scope="module")
def test_outdir(request):
    """Output directory for the test run."""

    # request.module == the name of the test module being run, e.g. test_remove_umi.py

    # Strip off the prepended 'test_'
    # type = module -> 'test_remove_umi' -> 'remove_umi'
    command_being_tested = request.module.__name__[5:]

    _test_outdir = os.path.join(BASE_OUTFILE_DIR, command_being_tested)

    # Remove any existing directory
    if _test_outdir[0] == '/':
        # safety check
        raise

    # Remove trace of any previous run
    shutil.rmtree(_test_outdir, True)

    # create the directory
    os.mkdir(_test_outdir)

    # run the tests
    yield _test_outdir

    # Remove the directory
    if not os.environ.get("SUPERDEDUPER_KEEP_TEST_DIRS"):
        shutil.rmtree(_test_outdir, True)

def to_eout_filename(fout_filename):
    """Convert filename of output file to filename of expected output file.

    Example:
        'files/last_run/remove_adapter/A_R1.rmadapt.fq'
        converts to
        'files/remove_adapter/eout/A_R1.rmadapt.fq'
    """

    elems = fout_filename.split('/')
    # -> ['files', 'last_run', 'remove_adapter', 'A_R1.rmadapt.fq']
    elems.remove(LAST_RUN_DIR)
    # -> ['files', 'remove_adapter', 'A_R1.rmadapt.fq']
    elems.insert(-1, EXPECTED_OUT_DIR)
    # -> ['files', 'remove_adapter', 'eout', 'A_R1.rmadapt.fq']
    return '/'.join(elems)
    # -> 'files/remove_adapter/eout/A_R1.rmadapt.fq'

def fix_paths(args, base_in, base_out, file_params):
    """Takes as input the docopt generated 'args' dict, and fixes all of the
    input/output paths.

    Example:
        args before = { ...
            '--adapter1': 'GATCGGAAGAGCACACG',
            '-o': None,
            '<in1.fastq>': 'A_R1.fq',
            '<in2.fastq>': 'A_R2.fq',
            '<input.fastq>': None,
            'remove-adapter': True
        ... }
        args after = { ...
            '--adapter1': 'GATCGGAAGAGCACACG',
            '-o': 'superdeduper/test/files/last_run/remove_adapter',
            '<in1.fastq>': 'superdeduper/test/files/remove_adapter/in/A_R1.fq',
            '<in2.fastq>': 'superdeduper/test/files/remove_adapter/in/A_R2.fq',
            '<input.fastq>': None,
            'remove-adapter': True
        ... }

    Args:
        args (dict): docopt generated args dictionary.
        base_in (str): Directory where the input files are stored.
            e.g. 'superdeduper/test/files/remove_adapter/in'
        base_out (str): Directory where the output files are placed.
            e.g. 'superdeduper/test/files/last_run/remove_adapter/'
        file_params ([str]): e.g. ['<input.fastq>' '<in1.fastq>', '<in2.fastq>']
    Returns
    """
    # Fix output dir path
    args['-o'] = base_out

    # Fix input file paths
    for param in file_params:
        filename = args[param]
        if filename is not None:
            args[param] = os.path.join(base_in, filename)
    return args

# vim: softtabstop=4:shiftwidth=4:expandtab

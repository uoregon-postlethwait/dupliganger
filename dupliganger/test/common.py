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

###############
### Imports ###
###############

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object
# py-lmdb uses bytes() for py3 and str() for py2.
# This package has different code for py2 and py3.
# And importing that future 'object' has a bug that screws up __slots__ in
# py2 (causes different behavior than in py3).

# Dupligänger imports

## Other imports

import pytest
import os
import shutil

#################
### Constants ###
#################

LAST_RUN_DIR            = 'last_run'
IN_DIR                  = 'in'
EXPECTED_OUT_DIR        = 'eout'
BASE_FILES_DIR          = 'dupliganger/test/files'
                          # e.g. 'dupliganger/test/files/last_run')
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
    if not os.environ.get("DUPLIGANGER_KEEP_TEST_DIRS"):
        shutil.rmtree(_test_outdir, True)

def to_eout_filename(fout_filename, python_version=None):
    """Convert filename of output file to filename of expected output file.

    If user passes optional python_version, then the tests expect different
    outputs for python version 2 vs version 3 (at time of writing, the only
    reason for this is the difference in python 2/3 pseudo random number
    generator) and so the files are put in a subdir named either 'py2' or
    'py3'.

    Example:
        'files/last_run/remove_adapter/A_R1.rmadapt.fq'
        converts to
        'files/remove_adapter/eout/A_R1.rmadapt.fq'

    Example of passing python_version=3:
        'files/last_run/remove_adapter/A_R1.rmadapt.fq'
        converts to
        'files/remove_adapter/eout/py3/A_R1.rmadapt.fq'

    Args:
        python_version (str): Optional; user specified a python_version (see
            above).
    """
    # Check reasonable python_version
    assert python_version in (2, 3, None)

    elems = fout_filename.split('/')
    # -> ['files', 'last_run', 'remove_adapter', 'A_R1.rmadapt.fq']
    just_filename = elems[-1]
    elems.remove(LAST_RUN_DIR)
    # -> ['files', 'remove_adapter', 'A_R1.rmadapt.fq']
    elems.insert(-1, EXPECTED_OUT_DIR)
    # -> ['files', 'remove_adapter', 'eout', 'A_R1.rmadapt.fq']
    if python_version is not None:
        elems.insert(-1, "py{}".format(python_version))
        # -> ['files', 'remove_adapter', 'eout', 'py3', 'A_R1.rmadapt.fq']
    feout_filename = '/'.join(elems)
    # -> 'files/remove_adapter/eout/A_R1.rmadapt.fq'

    # Leave these print statements here, otherwise very difficult to debug tox
    # output when one fails (because we're using pytest fixtures, so without
    # these print statements, impossible to tell which file it failed on).
    print("actual   output filename = {}".format(fout_filename))
    print("expected output filename = {}".format(feout_filename))
    print("just     the    filename = {}".format(just_filename))

    return feout_filename

def to_eout_db_dump_filename(alignment_file, db_name):
    """Convert filename of output file to filename of expected output file.

    Args:
        alignment_file (str): Name of the alignment file.
        db_name (str): Name of the db
    Example:
        args ('files/build_read_db/in/11_first_test.pe.sam', 'read_group_db')
        converts to
        'files/build_read_db/eout/11_first_test.pe.read_group_db'
    """

    if alignment_file[-4:] in ('.sam', '.bam'):
        # Chop off .sam or .bam extension
        alignment_file = alignment_file[:-4]

    elems = alignment_file.split('/')
    # -> ['files', 'build_read_db', 'in', '11_first_test.pe']
    elems.remove(IN_DIR)
    # -> ['files', 'build_read_db', '11_first_test.pe']
    elems.insert(-1, EXPECTED_OUT_DIR)
    # -> ['files', 'build_read_db', 'eout', '11_first_test.pe']
    eout = '/'.join(elems)
    # -> 'files/build_read_db/eout/11_first_test.pe'
    return '.'.join((eout, db_name))
    # -> 'files/build_read_db/eout/11_first_test.pe.read_group_db'

def fix_paths(args, base_in, base_out, file_params):
    """Takes as input the docopt generated 'args' dict, and fixes all of the
    input/output paths.

    Example:
        args before = { ...
            '-o': None,
            '<in1.fastq>': 'A_R1.fq',
            '<in2.fastq>': 'A_R2.fq',
            '<input.fastq>': None,
        ... }
        args after = { ...
            '-o': 'dupliganger/test/files/last_run/remove_adapter',
            '<in1.fastq>': 'dupliganger/test/files/remove_adapter/in/A_R1.fq',
            '<in2.fastq>': 'dupliganger/test/files/remove_adapter/in/A_R2.fq',
            '<input.fastq>': None,
        ... }

    Args:
        args (dict): docopt generated args dictionary.
        base_in (str): Directory where the input files are stored.
            e.g. 'dupliganger/test/files/remove_adapter/in'
        base_out (str): Directory where the output files are placed.
            e.g. 'dupliganger/test/files/last_run/remove_adapter/'
        file_params ([str]): e.g. ['<input.fastq>' '<in1.fastq>', '<in2.fastq>']

    Returns:
        dict: The modified args dict.

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

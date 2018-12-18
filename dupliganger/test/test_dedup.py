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

# Python 3 imports
from __future__ import absolute_import
from __future__ import division
from future import standard_library
standard_library.install_aliases()

# Dupligänger imports
from dupliganger.dedup import __doc__
from dupliganger.dedup import run, parse_args

# Dupligänger test library imports
from common import (fix_paths, test_outdir, to_eout_filename, BASE_OUTFILE_DIR,
        BASE_FILES_DIR)

## Other imports
import pytest
from docopt import docopt
import os

# For random number generator / py2/py3 differences.
import sys


#################
### Constants ###
#################

# e.g. 'test_dedup' -> 'dedup'
COMMAND_BEING_TESTED = __name__[5:]

# e.g. 'dupliganger/test/files/last_run/dedup'
OUTFILE_DIR = os.path.join(BASE_OUTFILE_DIR, COMMAND_BEING_TESTED)

# e.g. 'dupliganger/test/files/dedup/in'
INFILE_DIR = os.path.join(BASE_FILES_DIR, COMMAND_BEING_TESTED, 'in')

# Taken from the docstring of dedup
COMMAND_FILE_PARAMS = ['<alignment-file>']


#################
### Functions ###
#################

@pytest.fixture(scope="module", params=[
        # bioo
        'dedup --kit bioo --write-flagged-sam --no-write-sam-headers --store memory 11_first_test.pe.bioo.sam',
        'dedup --kit bioo --write-flagged-sam --no-write-sam-headers --store memory 12_one_dup_one_not.pe.bioo.sam',
        # doug
        'dedup --write-flagged-sam --no-write-sam-headers --store memory 13_first_test.pe.doug.sam',
        'dedup --write-flagged-sam --no-write-sam-headers --store memory 14_one_dup_one_not.pe.doug.sam',
    ])
def commands(request):
    """This is where the magic happens.

    This is a pytest fixture that is parameterized.  If you pass in this
    fixture to a given test, that test will be run once for each param in
    params.

    In this fixture, we are passing commandline strings to dupliganger
    dedup.

    See also "fix_paths()", which converts the simple filenames above to
    relative paths appropriate for this.
    """
    yield request.param


class TestDedup(object):
    """Test dedup."""

    #############
    ### Tests ###
    #############

    def test_run_all_fixture_commands(self, test_outdir, commands):
        """This test runs all the commands parameterized in the 'commands'
        fixture defined above.  (pytest is actually responsible for running the
        running this test once for each command / fixture parameter).

        Args:
            test_outdir (a fixture): This is the output directory into which
                all output files are placed.
            commands (a parameterized fixture): This boils down to actual
                command line arguments given to dupliganger.
        """

        # Get the arguments passed
        args = docopt(__doc__, help=False, argv=commands.split())
        # Fix input file path(s) and outdir path (prepend INFILE_DIR and OUTFILE_DIR)
        args = fix_paths(args, INFILE_DIR, OUTFILE_DIR, COMMAND_FILE_PARAMS)
        # Run dupliganger command!
        out_files = run(*parse_args(args))

        for fout in out_files:
            if fout == '/dev/null':
                # skip /dev/null's obviously...
                continue
            # Note that dedup.py uses python's pseudo-random number generator, and
            # the RNG differs between py2 and py3, so we pass fix_paths the python
            # version to get around this (we have to keep two versions of in/eout
            # files, one for py2 and one for py3).
            eout = to_eout_filename(fout, sys.version_info[0])
            with open(fout, 'r') as f, open(eout, 'r') as e:
                assert f.read() == e.read()

        # assert 0

# vim: softtabstop=4:shiftwidth=4:expandtab

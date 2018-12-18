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

from future import standard_library
standard_library.install_aliases()

# Dupligänger imports
from dupliganger.build_read_and_loc_dbs import __doc__
from dupliganger.build_read_and_loc_dbs import run, parse_args

# Dupligänger test library imports
from common import (fix_paths, test_outdir, to_eout_db_dump_filename,
        BASE_OUTFILE_DIR, BASE_FILES_DIR)

## Other imports
import pytest
from docopt import docopt
import os


#################
### Constants ###
#################

# e.g. 'test_build_read_and_loc_dbs' -> 'build_read_and_loc_dbs'
COMMAND_BEING_TESTED = __name__[5:]

# e.g. 'dupliganger/test/files/last_run/build_read_and_loc_dbs'
OUTFILE_DIR = os.path.join(BASE_OUTFILE_DIR, COMMAND_BEING_TESTED)

# e.g. 'dupliganger/test/files/build_read_and_loc_dbs/in'
INFILE_DIR = os.path.join(BASE_FILES_DIR, COMMAND_BEING_TESTED, 'in')

# Taken from the docstring of build-read-and-loc-dbs
COMMAND_FILE_PARAMS = ['<alignment-file>']


#################
### Functions ###
#################

@pytest.fixture(scope="module", params=[
        'build-read-and-loc-dbs --store memory 11_first_test.pe.sam',
        'build-read-and-loc-dbs --store lmdb 11_first_test.pe.sam',
        'build-read-and-loc-dbs --store memory 12_one_dup_one_not.pe.sam',
        'build-read-and-loc-dbs --store lmdb 12_one_dup_one_not.pe.sam',
        'build-read-and-loc-dbs --store memory 12_one_dup_one_not.pe.bam',
        'build-read-and-loc-dbs --store lmdb 12_one_dup_one_not.pe.bam',
    ])
def commands(request):
    """This is where the magic happens.

    This is a pytest fixture that is parameterized.  If you pass in this
    fixture to a given test, that test will be run once for each param in
    params.

    In this fixture, we are passing commandline strings to dupliganger
    build-read-and-loc-dbs.

    See also "fix_paths()", which converts the simple filenames above to
    relative paths appropriate for this.
    """
    yield request.param


class TestBuildReadAndLocDbs(object):
    """Test build-read-and-loc-dbs."""

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
        # Get alignment file...
        alignment_file = args['<alignment-file>']
        # Run dupliganger command!
        (parent_db, read_group_db, loc_db) = run(*parse_args(args))

        # 13_third_test.sam -> 13_third_test.read_group_db
        # 13_third_test.sam -> 13_third_test.read_name_db
        # 13_third_test.sam -> 13_third_test.loc_db

        for db_name in 'read_group_db loc_db'.split():
            # Get string representation of db
            db_repr = str(locals()[db_name])
            # Get expected out filename
            eout = to_eout_db_dump_filename(alignment_file, db_name)
            with open(eout, 'r') as e:
                assert db_repr == e.read()

        # assert 0

# vim: softtabstop=4:shiftwidth=4:expandtab


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
from dupliganger.remove_umi import __doc__
from dupliganger.remove_umi import run, parse_args

# Dupligänger test library imports
from common import (fix_paths, test_outdir, to_eout_filename, BASE_OUTFILE_DIR,
        BASE_FILES_DIR)

## Other imports
import pytest
from docopt import docopt
import os


#################
### Constants ###
#################

# e.g. 'test_remove_umi' -> 'remove_umi'
COMMAND_BEING_TESTED = __name__[5:]

# e.g. 'dupliganger/test/files/last_run/remove_umi'
OUTFILE_DIR = os.path.join(BASE_OUTFILE_DIR, COMMAND_BEING_TESTED)

# e.g. 'dupliganger/test/files/remove_umi/in'
INFILE_DIR = os.path.join(BASE_FILES_DIR, COMMAND_BEING_TESTED, 'in')

# Taken from the docstring of remove-umi
COMMAND_FILE_PARAMS = ['<input.fastq>', '<in1.fastq>', '<in2.fastq>',
        '<input.bam>']


#################
### Functions ###
#################

@pytest.fixture(scope="module", params=[
        'remove-umi 01_trailing_slash_R1.fq 01_trailing_slash_R2.fq',
        'remove-umi 02_no_trailing_slash_R1.fq 02_no_trailing_slash_R2.fq',
        'remove-umi 02_no_trailing_slash.fq',
        'remove-umi 06_pe_bam.bam',
        'remove-umi 06_se_bam.bam',
        'remove-umi 08_gzip_infile_R1.fq.gz 08_gzip_infile_R2.fq.gz',
        'remove-umi 08_gzip_infile.fq.gz',
    ])
def commands(request):
    """This is where the magic happens.

    This is a pytest fixture that is parameterized.  If you pass in this
    fixture to a given test, that test will be run once for each param in
    params.

    In this fixture, we are passing commandline strings to dupliganger
    remove-umi.

    See also "fix_paths()", which converts the simple filenames above to
    relative paths appropriate for this.
    """
    yield request.param


class TestRemoveUmi(object):
    """Test remove-umi."""

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
            eout = to_eout_filename(fout)
            with open(fout, 'r') as f, open(eout, 'r') as e:
                assert f.read() == e.read()

        # assert 0

# vim: softtabstop=4:shiftwidth=4:expandtab

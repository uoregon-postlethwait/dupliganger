# Copyright (C) 2014, 2015  Jason Sydes
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

# Python 3 imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# For version stuff...
import sys

# For timing
import time

# For exception reporting/logging
import traceback

# Minimum python version
VERSION_PYTHON_MINIMUM =                                (2, 7)

def main_wrapper():
    """Wraps main() in some handy niceness."""

    # Check python version first.
    if sys.version_info < VERSION_PYTHON_MINIMUM:
        print("SuperDeDuper requires Python {0} or later.  You are running {1}.".format(
            '.'.join([str(i) for i in VERSION_PYTHON_MINIMUM]),
            '.'.join([str(i) for i in sys.version_info[0:3]])))
        sys.exit(1)

    # Now you can safely do SuperDeDuper imports
    import superdeduper.superdeduper

    # Go
    superdeduper.superdeduper.main()


# vim: softtabstop=4:shiftwidth=4:expandtab

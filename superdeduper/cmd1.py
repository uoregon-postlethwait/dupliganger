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

"""usage: superdeduper cmd1 [options] [--] [<filepattern>...]

    -h, --help
    -n, --dry-run        dry run
    -v, --verbose        be verbose

    -i, --interactive    interactive picking
    -p, --patch          select hunks interactively
    -e, --edit           edit current diff and apply
    -f, --force          allow adding otherwise ignored files
    -u, --update         update tracked files
    -N, --intent-to-add  record only the fact that the path will be added later
    -A, --all            add all, noticing removal of tracked files
    --refresh            don't add, only refresh the index
    --ignore-errors      just skip files which cannot be added because of errors
    --ignore-missing     check if - even missing - files are ignored in dry run

"""

###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# version
from superdeduper._version import __version__

## SuperDeDuper imports
from superdeduper.constants import *
# from superdeduper.common import (
#     ConfigurationException,
#     CannotContinueException,
#     PrerequisitesException,
#     ArgumentTypeException,
#     pmsg,
#     perr,
#     Progress)
# from superdeduper.some_module import (SomeClass, SomeOtherClass)
# import superdeduper.other_module


## Other imports
from docopt import docopt


#################
### Constants ###
#################


#################
### Functions ###
#################


###############
### Classes ###
###############


############
### Main ###
############

def main(argv):
    print(docopt(__doc__))

# vim: softtabstop=4:shiftwidth=4:expandtab

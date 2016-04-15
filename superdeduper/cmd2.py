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


"""
usage: superdeduper cmd2 [options] [-r | -a] [--merged=<commit> | --no-merged=<commit>]
       superdeduper cmd2 [options] [-l] [-f] <branchname> [<start-point>]
       superdeduper cmd2 [options] [-r] (-d | -D) <branchname>
       superdeduper cmd2 [options] (-m | -M) [<oldbranch>] <newbranch>

Generic options
    -h, --help
    -v, --verbose         show hash and subject, give twice for upstream branch
    -t, --track           set up tracking mode
    --set-upstream        change upstream info
    --color=<when>        use colored output
    -r                    act on remote-tracking branches
    --contains=<commit>   print only branches that contain the commit
    --abbrev=<n>          use <n> digits to display SHA-1s

Specific superdeduper-cmd3 actions:
    -a                    list both remote-tracking and local branches
    -d                    delete fully merged branch
    -D                    delete branch (even if not merged)
    -m                    move/rename a branch and its reflog
    -M                    move/rename a branch, even if target exists
    -l                    create the branch's reflog
    -f, --force           force creation (when already exists)
    --no-merged=<commit>  print only not merged branches
    --merged=<commit>     print only merged branches

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

# import sys

# For superdeduper.log logging
# import logging
# import logging.config

# for debugging:
# import pprint
# import traceback

# for abstract base classes:
# from abc import ABCMeta, abstractmethod, abstractproperty

# for command line arguments
# import argparse

# For configuration file
# import ConfigParser

# For iterating!
# import itertools

# For timing things
# import time

# For quicker sorting (operator.[item|attr]getter)
# import operator



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

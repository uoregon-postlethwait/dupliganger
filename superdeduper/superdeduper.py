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
# Written by Jason Sydes


"""
SuperDeDuper

Usage: superdeduper [--version] [--help]
           [--some-flag] [--verbose]
           <command> [<args>...]

options:
   -c <name=value>
   -h, --help
   -p, --paginate

The most commonly used superdeduper commands are:
   cmd1       Some command 1.
   cmd2       Some command 2.

See 'superdeduper help <command>' for more information on a specific command.

"""

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# For Docopt
from docopt import docopt
import importlib

# version
from superdeduper._version import __version__
print __version__
__version_info__ = tuple(__version__.split('.'))

# Other imports


#################
### Functions ###
#################


##############################################
### Config File and Command Line Arguments ###
##############################################


###############
### Classes ###
###############


#######################
### Debug functions ###
#######################


############
### Main ###
############

def main():

    args = docopt(__doc__,
          version='superdeduper version {}'.format(__version__),
          options_first=True)
    # print('global arguments:')
    # print(args)
    # print('command arguments:')

    argv = [args['<command>']] + args['<args>']
    cmd = args['<command>']

    if args['<command>'] in 'cmd1 cmd2 cmd3'.split():
        cmd_module = importlib.import_module("superdeduper.{}".format(cmd))
        cmd_module.main(argv)
    elif cmd in ['help', None]:
        exit(call(['superdeduper', '--help']))
    else:
        exit("{} is not a superdeduper command. See 'superdeduper help'.".format(args['<command>']))


# vim: softtabstop=4:shiftwidth=4:expandtab

# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
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

"""Dupligänger

A reference-based, UMI-aware, 5'-trimming-aware PCR duplicate removal pipeline.

Usage: dupliganger [options] <command> [<args>...]


Dupligänger is a pipeline.  Each stage of the pipeline is run by passing a
'command' to Dupligänger.  The commands / pipeline-steps (in order) are as
follows:

   remove-umi       1. Annotate read names with UMIs (clip inline UMIs if needed).
   remove-adapter   2. Remove adapters ('Cutadapt' wrapper).
   qtrim            3. Quality trim ('Trimmomatic' wrapper).
   annotate-qtrim   4. Annotates quality trimmed file(s).
   align            5. Align reads to a reference genome assembly. -- NOT YET IMPLEMENTED
   dedup            6. Use the alignment to remove PCR duplicates.

While generally used only by the developers of Dupligänger, the 'dedup'
command is comprised of the following Dupligänger commands run in the
following order:

    build-read-db       1. Build a database of aligned reads.
    build-location-db   2. Build a database of locations of aligned reads.
    build-dup-db        3. Build a database of PCR duplicates.

Options:
    -o OUT_DIR      Place results in directory OUT_DIR.
    --compress      Compress output.
    --version       Show version.

Note:
    Dupligänger supports (and autodetects) input FASTQ files that are gzipped.

See 'dupliganger help <command>' for more information on a specific command.

"""

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# For Docopt
from docopt import docopt
import importlib

# version
from dupliganger import __version__
__version_info__ = tuple(__version__.split('.'))

# Other imports
import subprocess


#################
### Constants ###
#################

SDD_COMMAND_MODULES = ['remove_umi', 'barcode_split_quality_filter_umi_anno',
        'remove_adapter', 'qtrim', 'annotate_qtrim', 'prep', 'dedup',
        'build_read_and_loc_dbs', 'build_dup_db']

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
          version='dupliganger version {}'.format(__version__),
          options_first=True)

    cmd = args['<command>'].replace('-', '_')

    if cmd in SDD_COMMAND_MODULES:
        cmd_module = importlib.import_module("dupliganger.{}".format(cmd))
        cmd_module.main()
    elif cmd in ['help', None]:
        argv = args['<args>']
        if argv == []:
            exit(subprocess.call(['dupliganger', '--help']))
        elif argv[0].replace('-', '_') in SDD_COMMAND_MODULES:
            exit(subprocess.call(['dupliganger', argv[0], '--help']))
        else:
            exit("{} is not a dupliganger command. See 'dupliganger help'.".format(
                argv[0]))
    else:
        exit("{} is not a dupliganger command. See 'dupliganger help'.".format(args['<command>']))


if __name__ == "__main__":
    main()

# vim: softtabstop=4:shiftwidth=4:expandtab

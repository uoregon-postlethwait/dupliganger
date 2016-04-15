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

################
### Defaults ###
################

# The configuration file
DEFAULT_SUPERDEDUPER_CONFIG_FILE =                    "superdeduper.config"

#################
### Constants ###
#################

# SuperDeDuper log filename
LOG_FILENAME =                                           'superdeduper.log'
# Overall log level
LOG_LEVEL =                                                         'DEBUG'
# Log level for superdeduper.log
LOG_LEVEL_FOR_FILE =                                                 'INFO'
# Logging configuration dict
LOGGING = {
    'version': 1,
    'handlers': {
        #'console': {
        #    'class': 'logging.StreamHandler',
        #    'level': LOG_LEVEL,
        #},
        'file': {
            'class': 'logging.FileHandler',
            'level': LOG_LEVEL_FOR_FILE,
            'filename': LOG_FILENAME,
            'mode': 'w',
        }
    },
    'root': {
        'level': LOG_LEVEL,
        #'handlers': ['console', 'file']
        'handlers': ['file']
    },
}

# vim: softtabstop=4:shiftwidth=4:expandtab

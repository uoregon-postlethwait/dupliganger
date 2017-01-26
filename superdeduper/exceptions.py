# Copyright (C) 2016, 2017  Jason Sydes and Peter Batzel
#
# This file is part of SuperDeduper
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the License with this program.
#
# Written by Jason Sydes and Peter Batzel
# Design by Peter Batzel and Jason Sydes

##################
### Exceptions ###
##################

class ConfigurationException(Exception):
    """Something went wrong with the configuration section."""
class ExecutionException(Exception):
    """Something went wrong with the execution of an external command."""
class ControlFlowException(Exception):
    """Something went wrong with control flow logic."""
class CannotContinueException(Exception):
    """SuperDeDuper has encountered a situation from which it cannot continue."""
class PrerequisitesException(Exception):
    """SuperDeDuper is missing prerequisites (e.g. missing gsnap)."""
class ArgumentException(Exception):
    """Problem with command line arguments."""
class ParseException(Exception):
    """Something went wrong with parsing something."""
class HardClippingNotSupportedException(Exception):
    """Encountered sam file hard-clipping, which is not supported."""
class UnexpectedExtensionException(Exception):
    """Extension passed was not in expected extensions."""

# vim: softtabstop=4:shiftwidth=4:expandtab

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

import sys

# For progress and timing
import time

# For logging
import logging


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
    """SuperDeDuper is missing prerequisites (e.g. an out of date BBMap version)."""
class ArgumentTypeException(Exception):
    """Passed in the incorrect type of argument."""


#################
### Functions ###
#################

def some_function(args):
    """A utility function."""

def pmsg(msg):
    """SuperDeDuper Message.  Write a message to STDOUT and the
    superdeduper.log.

    You should *never* use print(), sys.stderr.write() or sys.stdout.write()
    within SuperDeDuper (except for the class Progress).  Instead, use this function.

    """
    logging.info(msg)
    print(msg)

def perr(msg):
    """SuperDeDuper Error Message.  Same as pmsg(), but it's an error instead
    of info."""

    logging.error(msg)
    print(msg)

def fmt_time(seconds):
    """Format number of seconds into a human readable time string.

    Example:

        Example::

            3601.5 ->  "3601.5s (or 1h0m)"
            1000.5 ->  "1000.5s (or 16m40s)"
            59.5 ->  "59.5s"

    Arguments:
        seconds (float): A length of time given in seconds.

    """
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    s = int(s)
    if h >= 1:
        return "{0:.1f}s (or {1}h{2}m)".format(int(seconds), h, m)
    elif m >= 1:
        return "{0:.1f}s (or {1}m{2}s)".format(seconds, m, s)
    else:
        return "{0:.1f}s".format(seconds)


def setup_logging(conf, time_start):
    """Setup superdeduper.log logging.

    Does the following:
        - configures the logging
        - adds a "header" line that includes the version and date
        - adds a line showing how SuperDeDuper was executed from the command line
        - dumps contents of superdeduper.config and samples_filelist to log

    Arguments:
        conf (Configuration): The Configuration singleton object.
        time_start (float): The time in seconds since the epoch.

    """
    # Configure logging
    logging.config.dictConfig(LOGGING)

    # First line of log, version + timedate.
    left = "SuperDeDuper! version {}.".format(__version__)
    right_len = 79 - len(left)
    pmsg("{}{:>{}}.".format(
        left, time.strftime('%l:%M:%S %p %Z on %b %d, %Y'), right_len))
    pmsg("")

    # Next, add how SuperDeDuper was run from the command line (only to the
    # log).
    args = sys.argv
    args[0] = os.path.basename(sys.argv[0])
    logging.info("Excecuted as:\n")
    logging.info("    {}".format(" ".join(args)))

    # Next, add the full contents of the configuration file.
    header = "=== Configuration File '{}' Contents ===".format(
        conf.general.config_file)
    logging.info("")
    logging.info("{:^79}".format(header))
    logging.info("")
    with open(os.path.expanduser(conf.general.config_file), 'r') as f:
        logging.info(f.read())

    # Next, add the full contents of the samples_filelist.
    header = "=== Samples Filelist '{}' Contents ===".format(
        conf.general.samples_filelist)
    logging.info("")
    logging.info("{:^79}".format(header))
    logging.info("")
    with open(os.path.expanduser(conf.general.samples_filelist), 'r') as f:
        logging.info(f.read())

    # Finally, add a header line for SuperDeDuper exection.
    header = "=== SuperDeDuper Execution ==="
    logging.info("{:^79}".format(header))
    logging.info("")


###############
### Classes ###
###############

class SomeSharedClass(object):
    """Some shared class that's useful."""
    pass


class Progress(object):
    """A simple progress meter printing to STDERR and superdeduper.log.

    We print to STDERR just for convenience because it's not buffered.

    """
    def __init__(self, progress_str, step=None, known_total=None, **kwargs):
        self.start = time.time()
        self.count = 0
        self.total = 0
        self.progress_str = progress_str
        self.known_total = None if known_total is None else int(known_total)
        self.step = None if step is None else int(step)
        self.indent = kwargs.get('indent', 0) * ' '
        sys.stderr.write("{}{}...".format(self.indent, progress_str))
        if self.step:
            sys.stderr.write('\n')

    def progress(self):
        if self.step:
            self.count += 1
            self.total += 1
            if self.count == self.step:
                if self.known_total:
                    sys.stderr.write("\r{}    {}/{} so far...".format(
                        self.indent, self.total, self.known_total))
                else:
                    sys.stderr.write("\r{}    {} so far...".format(
                        self.indent, self.total))
                self.count = 0
        else:
            sys.stderr.write('.')

    def done(self):
        _end = time.time()
        _secs = _end - self.start

        if not self.step:
            msg_mid = "{}{}...".format(self.indent, self.progress_str)
            sys.stderr.write('\r')
            sys.stderr.write(msg_mid)
            msg_mid = ""
        else:
            if self.known_total:
                msg_mid = "{}    {}/{} so far...".format(
                    self.indent, self.total, self.known_total)
                sys.stderr.write('\r')
                sys.stderr.write(msg_mid)
            else:
                msg_mid = "{}    {} so far...".format(self.indent, self.total)
                sys.stderr.write('\r')
                sys.stderr.write(msg_mid)

        msg_end = " done. (elapsed time: {})".format(fmt_time(_secs))
        sys.stderr.write(msg_end + '\n')

        # Now write full message to the log file.

        msg_beg = ("{}{}...".format(self.indent, self.progress_str))
        if self.step:
            msg_beg += '\n'
        logging.info(msg_beg + msg_mid + msg_end)


# vim: softtabstop=4:shiftwidth=4:expandtab

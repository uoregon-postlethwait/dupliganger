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

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object
# py-lmdb uses bytes() for py3 and str() for py2.
# This package has different code for py2 and py3.
# And importing that future 'object' has a bug that screws up __slots__ in
# py2 (causes different behavior than in py3).

from builtins import range

# Dupligänger imports
try:
    from dupliganger.constants import *
    from dupliganger.exceptions import *
except ImportError:
    from constants import *
    from exceptions import *

# version
from dupliganger import __version__
__version_info__ = tuple(__version__.split('.'))

# Other imports

import sys

# For progress and timing
import time

# For logging
import logging

# For pgopen, gzwrite, pigzopen
import contextlib
import os
import subprocess
import shlex

# For is_gzipped
import io

# For tmpfile names
import string
import random

# For bam
import gzip

# # For shell-like "which()"
try:
    from shutil import which
except ImportError:
    from whichcraft import which

# For memory usage.
import psutil
import resource

#################
### Functions ###
#################

def some_function(args):
    """A utility function."""

def pmsg(msg):
    """Dupligänger Message.  Write a message to STDOUT and the
    dupliganger.log.

    You should *never* use print(), sys.stderr.write() or sys.stdout.write()
    within Dupligänger (except for the class Progress).  Instead, use this function.

    """
    logging.info(msg)
    print(msg)

def perr(msg):
    """Dupligänger Error Message.  Same as pmsg(), but it's an error instead
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
    """Setup dupliganger.log logging.

    Does the following:
        - configures the logging
        - adds a "header" line that includes the version and date
        - adds a line showing how Dupligänger was executed from the command line
        - dumps contents of dupliganger.config and samples_filelist to log

    Arguments:
        conf (Configuration): The Configuration singleton object.
        time_start (float): The time in seconds since the epoch.

    """
    # Configure logging
    logging.config.dictConfig(LOGGING)

    # First line of log, version + timedate.
    left = "Dupligänger! version {}.".format(__version__)
    right_len = 79 - len(left)
    pmsg("{}{:>{}}.".format(
        left, time.strftime('%l:%M:%S %p %Z on %b %d, %Y'), right_len))
    pmsg("")

    # Next, add how Dupligänger was run from the command line (only to the
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

    # Finally, add a header line for Dupligänger exection.
    header = "=== Dupligänger Execution ==="
    logging.info("{:^79}".format(header))
    logging.info("")


@contextlib.contextmanager
def pgopen(num_threads, filename):
    """Context manager to open a plain or gzipped file for reading only.

    Read-only.  If num_threads > 1 and pigz is installed, it will use pigz to
    uncompress.

    Usage:
        with pgopen(file) as f:
            # do stuff...
    """
    # Determine if gzipped
    gzipped = False
    with io.open(filename, mode='rb') as f:
        # Is this a gzipped file? Check magic number.
        magic_num = f.read(2)
        f.seek(0)

        if magic_num == b'\x1f\x8b':
            gzipped = True

    if gzipped:
        # This is a gzipped file.
        if num_threads > 1 and which('pigz'):
            # pigz read
            cmd = shlex.split('unpigz -p {} -c {}'.format(num_threads, filename))
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=-1,
                    universal_newlines=True).stdout as f:
                yield f
        else:
            # gzip read
            cmd = shlex.split('gunzip -c {}'.format(filename))
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=-1,
                    universal_newlines=True).stdout as f:
                yield f
    else:
        # This is not a gzipped file.
        with asciiopen(filename) as f:
            yield f

@contextlib.contextmanager
def asciiopen(filename):
    """Context manager to open an ASCII encoded file across Python 2/3.

    Usage:
        with asciiopen(file) as f:
            # do stuff...
    """
    # So, basically, you came to the conclusion that you probably just
    # want to write a function 'asciiopen' which just opens up a file
    # differently depending on whether you're running python 2 or 3.
    # Why?
    # I fought with io.open a bunch, and here's how it behaves:
    #
    # Python 2:
    #   >>> type(io.open('ACTTGATG_R1.3300.fq', mode='r', encoding='ascii').readline())
    #   <type 'unicode'>
    # Python 3
    #   >>> type(io.open('ACTTGATG_R1.3300.fq', mode='r', encoding='ascii').readline())
    #   <class 'str'>
    #
    # The alternative is to read everything in as bytes, but python 3 is
    # weird about that as well:
    #   >>> a = io.open('ACTTGATG_R1.3300.fq', mode='rb')
    #   >>> b = a.readline()
    #   >>> b
    #   b'@D00597:180:C7NMDANXX:6:1101:1184:33231/1\n'
    #   >>> ascii(b)
    #   "b'@D00597:180:C7NMDANXX:6:1101:1184:33231/1\\n'"
    #
    # In the end, it's probably just easier to write an asciiopen()
    # function where in python3 it is:
    #   io.open('ACTTGATG_R1.3300.fq', mode='r', encoding='ascii'
    # and in python2 it is just the old "open".  Definitely do NOT do:
    #       from builtins import open
    #
    # There is perhaps a better way to do all this.  For now, this works.
    #
    if sys.version_info.major == 2:
        with open(filename, 'r') as f:
            yield f
    elif sys.version_info.major == 3:
        with io.open(filename, mode='r', encoding='ascii') as f:
            yield f

@contextlib.contextmanager
def bamopen(filename, silence_broken_pipe_errors=False):
    """Context manager to open a BAM file for reading only.

    Usage:
        with bamopen(file) as f:
            # do stuff...

    Args:
        filename (str): The filename to examine.
        silence_broken_pipe_errors (bool): If True, then pipe stderr to
            /dev/null.  This is useful if you only want to "peek" at the first
            few bytes / lines of a file; in that scenario, if you close before
            reading all the output, samtools will complain of a broken pipe.
    """

    cmd = shlex.split('samtools view -h {}'.format(filename))
    if silence_broken_pipe_errors:
        import os
        DEVNULL = open(os.devnull, 'wb')
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=-1,
                stderr=DEVNULL, universal_newlines=True).stdout as f:
            yield f
    else:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                bufsize=-1, universal_newlines=True).stdout as f:
            yield f

@contextlib.contextmanager
def sambamopen(filename):
    """Context manager to open a SAM or BAM file for reading only.

    Usage:
        with sambamopen(file) as f:
            # do stuff...

    Args:
        filename (str): The filename to examine.
    """

    cmd = shlex.split('samtools view -h {}'.format(filename))
    if is_bam(filename):
        with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                bufsize=-1, universal_newlines=True).stdout as f:
            yield f
    else:
        with pgopen(1, filename) as f:
            yield f

@contextlib.contextmanager
def gzwrite(filename):
    """Context manager to write to a gzipped file.

    Usage:
        with gzwrite(file) as f:
            # do stuff...
    """
    with open(filename, 'wb') as f:
        cmd = shlex.split('gzip -c')
        z = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=-1, stdout=f)
        try:
            yield z.stdin
        finally:
            z.stdin.close()
            z.wait()

@contextlib.contextmanager
def pigzwrite(num_threads, filename):
    """Context manager to write to a gzipped file with pigz.

    Usage:
        with gzwrite(num_threads, file) as f:
            # do stuff...
    """
    with open(filename, 'wb') as f:
        cmd = shlex.split('pigz -p {}'.format(num_threads))
        z = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=-1, stdout=f)
        try:
            yield z.stdin
        finally:
            z.stdin.close()
            z.wait()

def file_root(filename, expected_ext=None):
    """Given a filename, returns the root name to be used for new files.

    If the file is gzipped, strips that away first.

    Arguments:
        filename (str): The filename to work on.
        expected_ext ([str]): An array of expected filename extensions.  Will
            raise exception if doesn't match.

    >>> file_root('filename.fq')
    ('', 'filename', '.fq')
    >>> file_root('filename.fq.gz')
    ('', 'filename', '.fq.gz')
    >>> file_root('/path/to/filename.fq')
    ('/path/to', 'filename', '.fq')
    >>> file_root('filename.fq.gz', ['fq', 'fastq'])
    ('', 'filename', '.fq.gz')
    >>> file_root('filename.log', ['fq', 'fastq'])
    Traceback (most recent call last):
        ...
    CannotContinueException: Extension log was in not expected extensions ['fq', 'fastq']
    """

    dirname, basename = os.path.split(os.path.expanduser(filename))
    root, ext = os.path.splitext(basename)
    orig_ext = ext
    if ext in ('.gz', ):
        root, ext = os.path.splitext(root)
        orig_ext = ext + orig_ext
    ext = ext[1:]

    if expected_ext:
        if ext not in expected_ext:
            raise UnexpectedExtensionException(
                    "Extension {} was in not expected extensions {}".format(
                        ext, expected_ext))

    return (dirname, root, orig_ext)

def pe_file_root(pe_filename):
    """Given a paired-end filename, returns the root name to be used for new files.

    Will raise an exception if passed an R1 filename (why? so we don't
    accidentally use this function for single-end reads).

    If the file is gzipped, strips that away first.

    Arguments:
        pe_filename (str): The R2 paired end filename.

    Returns:
        (str, str, str): A 3-tuple: (the path, the pe_file_root, the original
                extension)

    >>> pe_file_root('/path/to/filename_R2.fq')
    ('/path/to', 'filename', '.fq')
    >>> pe_file_root('/path/to/filename_R2.fq.gz')
    ('/path/to', 'filename', '.fq.gz')
    >>> pe_file_root('/path/to/filename_R2_other_stuff.fq.gz')
    ('/path/to', 'filename_other_stuff', '.fq.gz')

    """
    dirname, root, orig_ext = file_root(pe_filename, ['fq', 'fastq'])

    if 'R1' in root or 'R2' not in root:
        raise CannotContinueException(
                 "pe_file_root should only be called with the R2 file.")

    if 'R2' in root.replace('R2', ''):
        m = "'R2' occurs more than once in {}, please change filename".format(
                 pe_filename)
        raise CannotContinueException(m)

    root = root.replace('_R2', '')
    return (dirname, root, orig_ext)

def se_log_filename(prefix, se_filename, suffix='out'):
    """Given a single-end (R1) filename, returns an appropriate log filename to
    be used for logging output of external tools.

    >>> se_log_filename('rmadapt', 'filename.fq')
    'exec.rmadapt.sr.filename_out'
    >>> se_log_filename('rmadapt', 'filename.fq.gz')
    'exec.rmadapt.sr.filename_out'
    >>> se_log_filename('rmadapt', 'filename_other_stuff.fq.gz')
    'exec.rmadapt.sr.filename_other_stuff.out'
    >>> se_log_filename('rmadapt', '/path/to/filename.fq')
    '/path/to/exec.rmadapt.sr.filename.out'

    """
    dirname, root, junk = file_root(se_filename, ['fq', 'fastq'])
    if not dirname or dirname == '.':
        return "exec.{}.sr.{}.{}".format(prefix, root, suffix)
    else:
        return "{}/exec.{}.sr.{}.{}".format(dirname, prefix, root, suffix)

def pe_log_filename(prefix, pe_filename, suffix='out'):
    """Given a paired-end (R2) filename, returns an appropriate log filename to
    be used for logging output of external tools.

    >>> pe_log_filename('rmadapt', 'filename_R2.fq')
    'exec.rmadapt.pe.filename.out'
    >>> pe_log_filename('rmadapt', 'filename_R2.fq.gz')
    'exec.rmadapt.pe.filename.out'
    >>> pe_log_filename('rmadapt', 'filename_R2_other_stuff.fq.gz')
    'exec.rmadapt.pe.filename_other_stuff.out'
    >>> pe_log_filename('rmadapt', '/path/to/filename_R2.fq')
    '/path/to/exec.rmadapt.pe.filename.out'

    """
    dirname, root, ext = pe_file_root(pe_filename)
    if not dirname or dirname == '.':
        return "exec.{}.pe.{}.{}".format(prefix, root, suffix)
    else:
        return "{}/exec.{}.pe.{}.{}".format(dirname, prefix, root, suffix)

def filename_in_to_out_fqgz(filename, suffix, gzip, outdir):
    """Converts a FASTQ filename to new filename with suffix, optionally gzipped.

    Examples:
        filename_in_to_out_fqgz('/path/to/file.fq.gz', 'stage1')
            -> ./file.stage1.fq.gz
        filename_in_to_out_fqgz('/path/to/file.fq.gz', 'stage1', False)
            -> ./file.stage1.fq
        filename_in_to_out_fqgz('/path/to/file.fq', 'stage1')
            -> ./file.stage1.fq.gz
        filename_in_to_out_fqgz('/path/to/file.fq.gz', 'stage1', True, 'outdir')
            -> outdir/file.stage1.fq.gz

    Args:
        filename (str): Name of file to transform.
        suffix (str): Suffix to add to filename.
        gzip (bool): Whether or not to add a "gz" on the end.
        outdir (Optional[str]): Directy to place filename in.

    Returns:
        str: The new filename.
    """
    dirname, root, junk = file_root(filename, ('fq', 'fastq'))
    ext = 'fq.gz' if gzip else 'fq'
    f = "{}.{}.{}".format(root, suffix, ext)
    return os.path.join(outdir, f)

def filename_in_to_out_sambam(filename, suffix, outdir):
    """Converts a BAM or SAM filename to new output filename with suffix.

    Args:
        filename (str): Name of file to transform.
        suffix (str): Suffix to add to filename.
        outdir (str): Directy to place filename in.

    Returns:
        str: The new filename.

    >>> filename_in_to_out_sambam('/path/to/file', 'dups_removed.sam', 'outdir')
    'outdir/file.dups_removed.sam'
    >>> filename_in_to_out_sambam('/path/to/file.sam', 'dups_removed.sam', 'outdir')
    'outdir/file.dups_removed.sam'
    >>> filename_in_to_out_sambam('/path/to/file.bam', 'dups_removed.sam', 'outdir')
    'outdir/file.dups_removed.sam'
    >>> filename_in_to_out_sambam('/path/to/file', 'dups_flagged.sam', 'outdir')
    'outdir/file.dups_flagged.sam'
    """
    try:
        dirname, root, junk = file_root(filename, ('sam', 'bam'))
    except(UnexpectedExtensionException):
        # Doesn't look like this file has a bam or sam extension
        dirname, root = os.path.split(os.path.expanduser(filename))

    f = "{}.{}".format(root, suffix)
    return os.path.join(outdir, f)

def filename_in_bam_to_out_fqgz(filename, suffix, gzip, paired, outdir):
    """Converts a BAM filename to new FASTQ single-end OR paired-end
    filename(s) with suffix, optionally gzipped.

    Args:
        filename (str): Name of file to transform.
        suffix (str): Suffix to add to filename.
        gzip (bool): Whether or not to add a "gz" on the end.
        paired (bool): True: paired-end data, False, single-end data.
        outdir (str): Directory to place filename in.

    Returns:
        [str]: The new filename(s).

    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', True, True, '.')
    ['./file_R1.stage1.fq.gz', './file_R2.stage1.fq.gz']
    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', False, True, '.')
    ['./file_R1.stage1.fq', './file_R2.stage1.fq']
    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', True, True, 'outdir')
    ['outdir/file_R1.stage1.fq.gz', 'outdir/file_R2.stage1.fq.gz']
    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', True, False, '.')
    ['./file.stage1.fq.gz']
    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', False, False, '.')
    ['./file.stage1.fq']
    >>> filename_in_bam_to_out_fqgz('/path/to/file.bam', 'stage1', True, False, 'outdir')
    ['outdir/file.stage1.fq.gz']
    """
    dirname, root, junk = file_root(filename, ('bam', 'BAM'))
    ext = 'fq.gz' if gzip else 'fq'
    if paired:
        f1 = "{}_R1.{}.{}".format(root, suffix, ext)
        f2 = "{}_R2.{}.{}".format(root, suffix, ext)
        fqgzs = [os.path.join(outdir, f1), os.path.join(outdir, f2)]
    else:
        f = "{}.{}.{}".format(root, suffix, ext)
        fqgzs = [os.path.join(outdir, f)]

    return fqgzs

def args_to_out_dir(args):
    """Convenience function to retrieve the output directory from args.

    Also mkdir the out_dir if it doesn't exist.

    Arguments:
        args (dict): Arguments from docopt.

    Returns:
        str: The name of the output directory.
    """

    if '-o' in args and args['-o'] is not None:
        out_dir = args['-o']
    elif '--out' in args and args['--out'] is not None:
        our_dir = args['--out']
    elif '--outdir' in args and args['--outdir'] is not None:
        our_dir = args['--outdir']
    elif '--out-dir' in args and args['--out-dir'] is not None:
        our_dir = args['--out-dir']
    else:
        out_dir = ""

    # Convert ~ to real path
    out_dir = os.path.expanduser(out_dir)

    try:
        os.mkdir(out_dir)
    except OSError:
        try:
            os.makedirs(out_dir)
        except OSError:
            pass

    # Confirm existence if not ""
    if out_dir != '' and not os.path.exists(out_dir):
        m = "Unable to create output directory {}".format(out_dir)
        raise CannotContinueException(m)

    return out_dir

def tmpf_start(*filenames):
    """Takes a list of filenames and returns "temporary" versions of those
    filenames. Works in conjuction with tmpf_finish().

    Handles gzipped files as well.

    Note: No actual files are created; only the names of files are created.

    Args:
        filename ([str]): The filename(s).
    Returns:
        [str]: A temporary version of the filename(s).
    """
    tmp_filenames = []
    for filename in filenames:
        if filename == os.devnull:
            # If you want /dev/null, it's not very temporary in nature.
            tmp_filenames.append(os.devnull)
            continue
        is_gzipped = False
        if filename[-3:] == '.gz':
            is_gzipped = True
            filename = filename[:-3]
        chars = string.ascii_lowercase + string.digits
        size = TMP_FILE_NAME_RANDOM_STR_SIZE
        random_str = ''.join(random.choice(chars) for _ in range(size))
        tmp_filename = "{}.tmp.{}".format(filename, random_str)
        if is_gzipped:
            tmp_filename += '.gz'
        tmp_filenames.append(tmp_filename)
    return tmp_filenames

def tmpf_finish(*tmp_filenames):
    """Makes a temporary version of a file permanent.  It strips off the
    '.tmp.XXXXXX' part of the filename, then renames (moves) the actual file.
    Does no checking to see if the file is still open (hopefully it isn't).

    Handles gzipped files as well.

    Args:
        tmp_filenames ([str]): The temporary name of the file(s).
    """
    final_filenames = []
    for tmp_filename in tmp_filenames:
        if tmp_filename == os.devnull:
            # If you want /dev/null, it's not very temporary in nature.
            continue
        is_gzipped = False
        if tmp_filename[-3:] == '.gz':
            is_gzipped = True
            tmp_filename = tmp_filename[:-3]
        size = len(".tmp.") + TMP_FILE_NAME_RANDOM_STR_SIZE
        filename = tmp_filename[:-size]
        ext = tmp_filename[-size:]
        assert(ext[0:5] == '.tmp.')
        if is_gzipped:
            tmp_filename += '.gz'
            filename += '.gz'
        final_filenames.append(filename)
        os.rename(tmp_filename, filename)
    return final_filenames

@contextlib.contextmanager
def tmpf_name(delete_temp_files_upon_failure, filename):
    """Context manager to manage naming of temporary files (for writing).  Does the
    following:
        * creates *temporary* filename
        * yields that filename back
        * Upon success, renames the temp file to permanent name ('filename').
        * Upon failure (an Exception), it will attempt to delete the temporary
          file.
    Args:
        delete_temp_files_upon_failure (bool): Whether or not to delete tmp
            files upon external failure.
        filename (str): Name of file to be written to.
    Yields:
        (str): The name of the temp file to be written to.
    """
    try:
        tmp_filename = tmpf_start(filename)[0]
        yield tmp_filename
    except Exception as e:
        if delete_temp_files_upon_failure:
            try:
                os.remove(tmp_filename)
            except Exception:
                # We catch and ignore this exception so as to not mask previous exceptions.
                pass
        raise e
    finally:
        try:
            tmpf_finish(tmp_filename)
        except Exception:
            # We catch and ignore this exception so as to not mask previous
            # exceptions.
            pass

@contextlib.contextmanager
def tmpf_open(fp_write, delete_temp_files_upon_failure, filename):
    """Context manager to open up temporary files for writing.  Does the
    following:
        * opens *temporary* output file for writing
        * yields that file back for writing
        * when finished writing, closes the file.
        * Upon success, renames the temp file to permanent name ('filename').
        * Upon failure (an Exception), it will attempt to delete the temporary
          file.
    Args:
        fp_write (function): Function to write file (eg write(), gzwrite()).
        delete_temp_files_upon_failure (bool): Whether or not to delete tmp
            files upon external failure.
        filename (str): Name of file to be written to.
    Yields:
        (file): A filehandle to the temp file.
    """
    try:
        tmp_filename = tmpf_start(filename)[0]
        with fp_write(tmp_filename) as f:
            yield f
    except Exception as e:
        if delete_temp_files_upon_failure:
            try:
                os.remove(tmp_filename)
            except Exception:
                # We catch and ignore this exception so as to not mask previous exceptions.
                pass
        raise e
    finally:
        try:
            tmpf_finish(tmp_filename)
        except Exception:
            # We catch and ignore this exception so as to not mask previous exceptions.
            pass

def is_gzipped(filename):
    """Determines if the file is gzipped or not. Uses magic number.

    Args:
        filename (str): The file to examine.
    Returns:
        bool: True if it is a gzipped file, False otherwise.
    """
    with io.open(filename, mode='rb') as f:
        # Is this a gzipped file? Check magic number.
        magic_num = f.read(2)

    return magic_num == b'\x1f\x8b'

def is_bam(filename):
    """Determines if the file is a BAM file or not. Uses magic number.

    Args:
        filename (str): The file to examine.
    Returns:
        bool: True if it is a BAM file, False otherwise.
    """
    try:
        with gzip.open(filename, 'rb') as f:
            magic_num = f.read(3)
            if magic_num == b'BAM':
                return True
            else:
                return False
    except IOError:
        # If it's not gzipped, then it's not a BAM.
        return False

def is_paired_bam(filename):
    """Detects if a BAM file is paired.

    Args:
        filename (str): The file to examine.
    Returns:
        bool: True if it is a paired BAM file, False otherwise.
    """
    assert(is_bam(filename))

    name1 = None
    name2 = None

    with bamopen(filename, True) as f:
        name1 = f.readline().split()[0]
        name2 = f.readline().split()[0]

    return name1 == name2

def setup_report_db():
    """Sets up a key-value pair "Report Database" to track metrics."""

    report_db = {}
    for metric in REPORT_DB_COUNT_METRICS:
        report_db[metric] = 0
    for metric in REPORT_DB_8_UMI_DIST_COUNT_METRICS:
        for i in range(1,9):
            report_db["{}{}".format(metric, i)] = 0

    return report_db

def memory_info(report_in_MBytes=False):
    """Report current memory used and maximum RSS memory consumed.  Results are
    in 'bytes' by default; passing 'report_in_MBytes' returns results in
    megabytes.

    Returns:
        (float, float): A two-tuple.  First member is current memory used,
            second member is maximum memory used.
    """

    # Currently used memory.
    process = psutil.Process(os.getpid())
    try:
        # py2
        curr_mem = process.get_memory_info().rss
    except(AttributeError):
        # py3
        curr_mem = process.memory_info().rss

    # Maximum memory (RSS) used.
    if sys.platform == 'darwin':
        max_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    else:
        max_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024

    if report_in_MBytes:
        return (curr_mem / 1024**2, max_mem / 1024**2)
    else:
        return (curr_mem, max_mem)

###############
### Classes ###
###############

class SomeSharedClass(object):
    """Some shared class that's useful."""
    pass

class Progress(object):
    """A simple progress meter printing to STDERR and dupliganger.log.

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

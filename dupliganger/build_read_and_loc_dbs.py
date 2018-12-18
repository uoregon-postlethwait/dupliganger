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

"""Build databases of aligned reads and their locations.

You probably don't want to run this command.

'build-read-and-loc-dbs' is a subcommand of the 'dedup' command.

You probably want to run the 'dedup' command instead.


Usage:
    dupliganger build-read-and-loc-dbs [options] <alignment-file>


Options:
    -h, --help
    -v, --verbose        Be verbose
    -o OUT_DIR           Place results in directory OUT_DIR.
    -k KIT, --kit KIT    The kit used [default: bioo].
    -t N, --threads N    Number of threads.
    --store STORE        Storage backend: 'lmdb' or 'memory' [default: lmdb]
    --debug-switch S     Fun debug switch [default: nothing].
    --debug-dump-rg-db   Dump the ReadGroup database (for debugging purposes only).
    --debug-dump-loc-db  Dump the Location database (for debugging purposes only).

"""

###############
### Imports ###
###############

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object
# py-lmdb uses bytes() for py3 and str() for py2.
# This package has different code for py2 and py3.
# And importing that future 'object' has a bug that screws up __slots__ in
# py2 (causes different behavior than in py3).

from builtins import ascii

# Dupligänger imports
from dupliganger.constants import *
from dupliganger.exceptions import *
from dupliganger.common import (setup_report_db, sambamopen, args_to_out_dir,
        memory_info)
from dupliganger.db import (ParentDbDict, ParentDbLmdb, SimpleBucketDict,
        SimpleBucketLmdb, LocationBucketDb, SimpleObjectDbDict,
        SimpleObjectDbLmdb)
from dupliganger.sam import (Read, ReadGroup, to_location_key_with_5p_trimming)

# debug
from dupliganger.db import DebugMultipleLocationBucketDbs

## Other imports
from docopt import docopt

# For filename fixing
import os

# For debug timing
import time

# For some printing to stdout
import sys

#################
### Constants ###
#################


#################
### Functions ###
#################

def write_to_read_and_location_dbs(report_db, fin, parent_db, read_group_db,
        location_db, records_per_txn):
    """Read SAM file, populate ReadGroupDb and BucketDb..."""
    first_loop = True
    done = False
    time1 = None
    time2 = None
    time_in_write_db = 0
    read_group_id = 1
    curr_read_group = ReadGroup()

    while (not done):
        # Writing read_group_db (and optionally, location_db)...
        if first_loop:
            first_loop = False
        else:
            time2 = time.time()
            time_in_write_db += (time2 - time1)
            print("Commit at read_group_id = {}, time taken = {}, current mem MBs: {}".format(
                    read_group_id, time2 - time1, memory_info(True)))
        time1 = time.time()
        with parent_db.begin(True) as txn:
            # functions
            fp_put_read_group = read_group_db.fp_put(txn)
            # fp_put_read_name = read_name_db.fp_put(txn)
            fp_append_location_db = location_db.fp_append(txn)
            (done, read_group_id, curr_read_group) = (
                    write_to_read_and_location_dbs_txn(report_db, fin,
                        read_group_id, curr_read_group, records_per_txn,
                        fp_put_read_group, fp_append_location_db))

def write_to_read_and_location_dbs_txn(report_db, fin, read_group_id,
        curr_read_group, records_per_txn, fp_put_read_group,
        fp_append_location_db):
    """
    Write a 'records_per_txn' number of reads and optionally locations to DB.

    Args:
        read_group_id (int): The current (or starting) read_group_id.
        curr_read_group (ReadGroup): Any leftover read_groups from previous txn are
            passed along here.
        records_per_txn (int): The number of records
        fp_put_read_group (function): Function to add a read_group to the
            read_group database.
        fp_append_location_db (function): Function to append a read_group_id to the
            genomic location database.
    Returns:
        (bool, int, [str]): 3-tuple with elements a) done or not, b) current
            read_group_id, c) current unwritten/incomplete read_group.

    """
    record_count = 0
    total_count = 0
    read = None
    remaining_lines = True
    # Used to keep keys ordered.
    read_group_id_str = ascii(read_group_id).zfill(READ_GROUP_ID_DIGITS)

    if len(curr_read_group) == 0:
        # First txn
        read_group = ReadGroup()
        prev_read = None
    else:
        # Leftover read_group not written in last txn.
        read_group = curr_read_group
        prev_read = curr_read_group[-1]

    while remaining_lines and record_count < records_per_txn:
        while True: # Assumption: average len(read_group) << records_per_txn
            # Collect all reads with same RNAME
            total_count += 1
            line = fin.readline().rstrip()
            if not line:
                read = None
                remaining_lines = False
                break
            if line[0] == '@':
                # skip header lines
                continue
            read = Read(line)
            if prev_read and prev_read.qname != read.qname:
                # New read name found, write to store current read_group.
                break
            else:
                read_group.append(read)
                prev_read = read

        if prev_read:
            # Writing to store
            read_name = read_group[0].qname.split(DELIM_ANNO)[0]
            fp_put_read_group(read_group_id_str, read_group)
            fp_append_location_db(read_group_id_str, read_group)
            report_db[LOG_NUM_READ_GROUPS] += 1

        # Prep for next round
        read_group = ReadGroup([read]) if read else ReadGroup()

        prev_read = read
        record_count += 1
        read_group_id += 1
        read_group_id_str = ascii(read_group_id).zfill(READ_GROUP_ID_DIGITS)
        if not remaining_lines:
            break

    if not remaining_lines and len(read_group) > 0:
        # Get the very last read_group of the file
        fp_put_read_group(read_group_id_str, read_group)
        fp_append_location_db(read_group_id_str, read_group)
        report_db[LOG_NUM_READ_GROUPS] += 1

    done = not remaining_lines
    return (done, read_group_id, read_group)

def parse_args(args):
    """Parse the command line arguments."""
    debug_switch = args['--debug-switch']
    dump_rg_db = args['--debug-dump-rg-db']
    dump_loc_db = args['--debug-dump-loc-db']

    # Convert ~ to real path
    input_file = os.path.expanduser(args['<alignment-file>'])

    # Which kit?
    kit = args['--kit']
    if kit == KIT_BIOO:
        pass
    else:
        raise CannotContinueException("""Kit {} is not supported.""".format(kit))

    # Figure out which function to use to write to output file.
    num_threads = args['--threads']

    # Which store to use
    if args['--store'] not in (STORE_OPTION_LMDB, STORE_OPTION_MEMORY):
        raise CannotContinueException("""Store {} is not supported.""".format(args['--store']))
    store = args['--store']

    outdir = args_to_out_dir(args)

    return (kit, store, outdir, input_file, debug_switch, dump_rg_db,
            dump_loc_db)

def run(kit, store, outdir, input_file, debug_switch, dump_rg_db, dump_loc_db):
    """Start the run.

    Args:
        kit (str): kit...
        store (str): Which storage backend to use.
        outdir (str): Output directory for results
        input_dir (str): ...
    """

    if not os.path.isfile(input_file):
        raise CannotContinueException('Input file {} does not exist.'.format(
                input_file))

    report_db = setup_report_db()
    if store == STORE_OPTION_LMDB:
        db_file = os.path.join(outdir, os.path.split(input_file)[1] + '.sdd.db')
        parent_db = ParentDbLmdb(db_file, LMDB_MAX_DBS, LMDB_DB_SIZE)
        read_group_db = SimpleObjectDbLmdb('read_group', parent_db, parent_db.env, ReadGroup)
        # read_name_db = SimpleObjectDbLmdb('read_name', parent_db, parent_db.env, int)
        location_bucket_store = SimpleBucketLmdb('location_bucket_store',
                parent_db, parent_db.env, DELIM_BUCKET_LIST, str)
    elif store == STORE_OPTION_MEMORY:
        parent_db = ParentDbDict()
        read_group_db = SimpleObjectDbDict()
        # read_name_db = SimpleObjectDbDict()
        location_bucket_store = SimpleBucketDict()

    loc_db = LocationBucketDb(location_bucket_store, to_location_key_with_5p_trimming)

    with sambamopen(input_file) as fin:
        write_to_read_and_location_dbs(report_db, fin, parent_db,
                read_group_db, loc_db, RECORDS_PER_TXN)

    if dump_rg_db:
        sys.stderr.write(str(read_group_db))
    if dump_loc_db:
        sys.stderr.write(str(loc_db))

    return (parent_db, read_group_db, loc_db)


###############
### Classes ###
###############


############
### Main ###
############

def main():
    args = docopt(__doc__)
    run(*parse_args(args))

# vim: softtabstop=4:shiftwidth=4:expandtab

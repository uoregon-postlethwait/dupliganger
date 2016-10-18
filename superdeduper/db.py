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


###############
### Imports ###
###############

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.common import (HardClippingNotSupportedException)

### DEBUGGING
from superdeduper.sam import (to_location_key_with_5p_trimming)

## Other imports

# For filename fixing
import os

# For writing errors about hard clipping
import sys

# For function partials
import functools

# For annotation database
import lmdb

# # For database stuff
import contextlib

#################
### Constants ###
#################


#################
### Functions ###
#################


###############
### Classes ###
###############

class ParentDb(object):
    pass

class ParentDbLmdb(ParentDb):
    """Parent database object.  Basically just wraps py-lmdb's Environment object."""
    __slots__ = ('env', )
    def __init__(self, filename, max_dbs, map_size):
        self.env = lmdb.open(filename, max_dbs=max_dbs, map_size=map_size)
    @contextlib.contextmanager
    def begin(self, write=False):
        with self.env.begin(write=write) as txn:
            yield txn

class ParentDbDict(ParentDb):
    """Let our python dict databases act like our LMDB databases."""
    @contextlib.contextmanager
    def begin(self, junk=False):
        yield TxnDict()

class TxnDict(object):
    """Dummy class to allow our ReadGroupDbDict class to act like a
    ReadGroupDbLmdb class."""
    @staticmethod
    def cursor(db_dict):
        return db_dict.iteritems()

class SimpleObjectDb(object):
    """A simple database in which a string key points to a string value which
    is converted to an object by the class passed to this database upon
    initialization.
    """
    __slots__ = ('db', 'item_class')

class SimpleObjectDbLmdb(SimpleObjectDb):
    def __init__(self, db_name, env, item_class):
        """
         Note: The item_class needs to implement the load() and the __repr__()
             method, which loads the bytes from the LMDB database.  In other
             words, the item_class defines and is entirely responsible for its
             string/bytes representation in the LMDB, and conversion back and
             forth.
         Args:
            db_name (str): Name of the database.
            env (lmdb.Environment): An LMDB environment.
            item_class (type): The class of item being stored.
        """
        self.db = env.open_db(db_name)
        self.item_class = item_class
    def fp_get(self, txn):
        return functools.partial(self.get, txn)
    def fp_put(self, txn):
        return functools.partial(self.put, txn)
    def get(self, txn, obj_id):
        """Cousin of convert()"""
        item_bytes = txn.get(bytes(obj_id), db=self.db)
        return self.item_class().load(item_bytes)
    def put(self, txn, obj_id, item):
        item_bytes = bytes(str(item))
        txn.put(bytes(obj_id), item_bytes, db=self.db)
    def convert(self, item_bytes):
        """Cousin of get()."""
        # print "DEBUG item_class is {}".format(self.item_class)
        # print "DEBUG item_bytes is {}".format(item_bytes)
        return self.item_class().load(item_bytes)

class SimpleObjectDbDict(SimpleObjectDb):
    def __init__(self, _1=None, _2=None, _3=None):
        self.db = {}
    def fp_get(self, _):
        return functools.partial(self.get, _)
    def fp_put(self, _):
        return functools.partial(self.put, _)
    def get(self, _, obj_id):
        return self.db[obj_id]
    def put(self, _, obj_id, item):
        self.db[obj_id] = item
    def convert(self, thing):
        return thing

class SimpleBucket(object):
    """A simple database, with string keys (string cheese?), which point at a
    simple list of members, separated by a delimiter (e.g. ',' or '\t')."""
    __slots__ = ('db', 'delim', 'item_class')

class SimpleBucketLmdb(SimpleBucket):
    def __init__(self, db_name, env, delim, item_class):
        """
         Args:
            db_name (str): Name of the database.
            env (lmdb.Environment): An LMDB environment.
            delim (str): The delimiter to separate values.
            item_class (type): The class of item being stored.
        """
        self.db = env.open_db(db_name)
        self.delim = delim
        self.item_class = item_class
    def fp_get(self, txn):
        return functools.partial(self.get, txn)
    def fp_put(self, txn):
        return functools.partial(self.put, txn)
    def fp_append(self, txn):
        return functools.partial(self.append, txn)
    def fp_append_many(self, txn):
        return functools.partial(self.append_many, txn)

    def get(self, txn, bucket_id):
        items_bytes = txn.get(bytes(bucket_id), db=self.db).split(self.delim)
        return [ self.item_class(item) for item in items_bytes ]
    def put(self, txn, bucket_id, items):
        items_bytes = bytes(self.delim.join([str(item) for item in items]))
        txn.put(bytes(bucket_id), items_bytes, db=self.db)
    def append(self, txn, bucket_id, item):
        existing = txn.get(bytes(bucket_id), db=self.db)
        if existing:
            items_concat = self.delim.join((existing, str(item)))
        else:
            items_concat = str(item)
        txn.put(bytes(bucket_id), bytes(items_concat), db=self.db)
    def append_many(self, txn, bucket_id, items):
        existing = txn.get(bytes(bucket_id))
        if existing:
            items_concat = self.delim.join((existing, self.delim.join(items)))
        else:
            items_concat = self.delim.join(items)
        txn.put(bytes(bucket_id), bytes(items_concat), db=self.db)
    def convert(self, items_concat):
        items_bytes = items_concat.split(self.delim)
        return [ self.item_class(item) for item in items_bytes ]

class SimpleBucketDict(SimpleBucket):
    def __init__(self, _1=None, _2=None, _3=None):
        self.db = {}
    def fp_get(self, junk):
        return functools.partial(self.get, junk)
    def fp_put(self, junk):
        return functools.partial(self.put, junk)
    def fp_append(self, junk):
        return functools.partial(self.append, junk)
    def fp_append_many(self, junk):
        return functools.partial(self.append_many, junk)

    def get(self, junk, bucket_id):
        return self.db[bucket_id]
    def put(self, junk, bucket_id, items):
        self.db[bucket_id] = items
    def append(self, junk, bucket_id, item):
        self.db.setdefault(bucket_id, [])
        self.db[bucket_id].append(item)
    def append_many(self, junk, bucket_id, items):
        self.db.setdefault(bucket_id, [])
        self.db[bucket_id] += items

    def convert(self, thing):
        return thing

class LocationBucketDb(object):
    """A location database, mostly just a simple wrapper around a) a
    SimpleBucket, and b) a function pointer that specifies how to turn a
    ReadGroup into a location_key to be used for lookups in this db.
    """

    __slots__ = 'db fp_to_location_key'.split()

    def __init__(self, db, fp_to_location_key):
        """
         Args:
            db (SimpleBucket): Store for this database wrapper..
            fp_to_location_key (function): A function that converts a read
                group (i.e. list of Read objects) to a genomic location to be
                used as the key to the LocationBucketDb.
        """
        self.db = db
        self.fp_to_location_key = fp_to_location_key

    def fp_append(self, txn):
        return functools.partial(self.append, txn)

    def append(self, txn, read_group_id, read_group):
        try:
            loc_key = self.fp_to_location_key(read_group)
            self.db.append(txn, loc_key, read_group_id)
        except HardClippingNotSupportedException:
            m = ("WARNING: Encountered hard-clipped read(s). Hard clipping "
                " not supported. Dropping read(s). Here's the read(s): {}\n"
                .format(read_group))
            sys.stderr.write(m)

class DebugMultipleLocationBucketDbs(object):
    """Just like LocationBucketDb, except it's many in one. FOR DEBUGGING."""

    __slots__ = 'db1 db2'.split()

    def __init__(self, simple_bucket_class, env, delim, item_class):
        self.db1 = simple_bucket_class('debug_location_bucket_store1', env, delim,
                item_class)
        self.db2 = simple_bucket_class('debug_location_bucket_store2', env, delim,
                item_class)

    def fp_append(self, txn):
        return functools.partial(self.append, txn)

    def append(self, txn, read_group_id, read_group):
        loc_key1 = to_location_key_with_5p_trimming(read_group)
        self.db1.append(txn, loc_key1, read_group_id)


############
### Main ###
############

# vim: softtabstop=4:shiftwidth=4:expandtab

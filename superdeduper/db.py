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

# Python 2/3 compatibility imports
from __future__ import absolute_import, division, print_function

# NOTE: Do *not* do the following:
# from builtins import str, chr, object
# py-lmdb uses bytes() for py3 and str() for py2.
# This package has different code for py2 and py3.
# And importing that future 'object' has a bug that screws up __slots__ in
# py2 (causes different behavior than in py3).

# For iterating over dicts in py23
from future.utils import iteritems

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.exceptions import *

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
    """Dummy class.  Does nothing except help others not complain."""

class SimpleObjectDb(object):
    """A simple database in which a string key points to a string value which
    is converted to an object by the class passed to this database upon
    initialization.
    """
    __slots__ = ('db', 'item_class')

    def __str__(self):
        """String representation of this db. For testing. Produces a
        dictionary-like output, sorted by key."""
        s = ''
        for k, v in sorted(iteritems(self.to_dict())):
            s += '{}: {}\n'.format(k,v)
        return s

class SimpleObjectDbLmdb(SimpleObjectDb):

    def __init__(self, db_name, parent_db, env, item_class):
        """
         Note: The item_class needs to implement the load() and the __repr__()
             method, which loads the bytes from the LMDB database.  In other
             words, the item_class defines and is entirely responsible for its
             string/bytes representation in the LMDB, and conversion back and
             forth.
         Args:
            db_name (str): Name of the database.
            parent_db (ParentDbLmdb): The LMDB parent database.
            env (lmdb.Environment): An LMDB environment.
            item_class (type): The class of item being stored.
        """
        if sys.version_info.major == 3:
            self.db = env.open_db(bytes(db_name, encoding='latin-1'))
        elif sys.version_info.major == 2:
            self.db = env.open_db(db_name)
        self.parent_db = parent_db
        self.item_class = item_class

    def to_dict(self):
        """Build a dictionary version of this LMDB. For testing."""
        d = {}
        with self.parent_db.begin() as txn:
                for key, val in self.iteritems(txn):
                    d[key] = val
        return d

    def fp_get(self, txn):
        return functools.partial(self.get, txn)
    def fp_put(self, txn):
        return functools.partial(self.put, txn)

    if sys.version_info.major == 3:

        def iteritems(self, txn):
            """Returns an items iterator."""
            for key, val in iter(txn.cursor(self.db)):
                yield (key.decode('latin-1'), self.convert(val))

        def get(self, txn, obj_id):
            """Cousin of convert()"""
            item_bytes = txn.get(bytes(obj_id, encoding='latin-1'), db=self.db)
            return self.item_class().load(item_bytes.decode())

        def put(self, txn, obj_id, item):
            """Python3 version of put.
            Args:
                obj_id (str): The ID of the item.
            """
            obj_id_bytes = bytes((obj_id), encoding='latin-1')
            item_bytes = bytes(str(item), encoding='latin-1')
            txn.put(obj_id_bytes, item_bytes, db=self.db)

        def convert(self, item_bytes):
            """Cousin of get(). Python3 version of convert()."""
            return self.item_class().load(item_bytes.decode())

    elif sys.version_info.major == 2:

        def iteritems(self, txn):
            """Returns an items iterator."""
            for key, val in iter(txn.cursor(self.db)):
                yield (key, self.convert(val))

        def get(self, txn, obj_id):
            """Cousin of convert()"""
            item_bytes = txn.get(obj_id, db=self.db)
            return self.item_class().load(item_bytes)

        def put(self, txn, obj_id, item):
            """Python2 version of put.
            Args:
                obj_id (str): The ID of the item.
            """
            item_str = repr(item)
            txn.put(obj_id, item_str, db=self.db)

        def convert(self, item_repr):
            """Cousin of get(). Python2 version of convert()."""
            return self.item_class().load(item_repr)

class SimpleObjectDbDict(SimpleObjectDb):
    def __init__(self, _1=None, _2=None, _3=None):
        self.db = {}
    def iteritems(self, _):
        """Returns an items iterator. (Note: the extra iter() call is necessary
        to make this work in py3.)"""
        return iter(iteritems(self.db))
    def fp_get(self, _):
        return functools.partial(self.get, _)
    def fp_put(self, _):
        return functools.partial(self.put, _)
    def get(self, _, obj_id):
        return self.db.get(obj_id)
    def put(self, _, obj_id, item):
        self.db[obj_id] = item
    def convert(self, thing):
        return thing
    def to_dict(self):
        return self.db

class SimpleBucket(object):
    """A simple database, with string keys (string cheese?), which point at a
    simple list of members, separated by a delimiter (e.g. ',' or '\t')."""
    __slots__ = ('db', 'delim', 'item_class', 'db_name')
    def __str__(self):
        """String representation of this db. For testing. Produces a
        dictionary-like output, sorted by key."""
        s = ''
        for k, v in sorted(iteritems(self.to_dict())):
            s += '{}: {}\n'.format(k,v)
        return s

class SimpleBucketLmdb(SimpleBucket):
    def __init__(self, db_name, parent_db, env, delim, item_class):
        """
         Args:
            db_name (str): Name of the database. (For debugging purposes only I
                believe.)
            parent_db (ParentDbLmdb): The LMDB parent database.
            env (lmdb.Environment): An LMDB environment.
            delim (str): The delimiter to separate values.
            item_class (type): The class of item being stored.
        """
        if sys.version_info.major == 3:
            self.db = env.open_db(bytes(db_name, encoding='latin-1'))
        elif sys.version_info.major == 2:
            self.db = env.open_db(db_name)
        self.parent_db = parent_db
        self.delim = delim
        self.item_class = item_class
        # Next line just for occassional debuggin.
        self.db_name = db_name

    def to_dict(self):
        """Build a dictionary version of this LMDB. For testing."""
        d = {}
        with self.parent_db.begin() as txn:
                for key, val in self.iteritems(txn):
                    d[key] = val
        return d

    def fp_get(self, txn):
        return functools.partial(self.get, txn)
    def fp_put(self, txn):
        return functools.partial(self.put, txn)
    def fp_append(self, txn):
        return functools.partial(self.append, txn)
    def fp_append_many(self, txn):
        return functools.partial(self.append_many, txn)

    if sys.version_info.major == 3:

        def iteritems(self, txn):
            """Returns an items iterator."""
            for key, val in iter(txn.cursor(self.db)):
                yield (key.decode('latin-1'), self.convert(val))

        def get(self, txn, bucket_id):
            items_str = txn.get(bytes(bucket_id, encoding='latin-1'),
                    db=self.db)
            if items_str is None:
                return None
            elif self.item_class == str:
                return items_str.decode().split(self.delim)
            else:
                return [ self.item_class(item) for item in
                        items_str.decode().split(self.delim) ]

        def put(self, txn, bucket_id, items):
            assert type(items) is list or type(items) is tuple
            bucket_id_bytes = bytes(bucket_id, encoding='latin-1')
            items_bytes = bytes(self.delim.join([str(item) for item in items]),
                    encoding='latin-1')
            txn.put(bucket_id_bytes, items_bytes, db=self.db)

        def convert(self, items_concat):
            """
            Args:
                items_concat (bytes): Items as bytes, concatenated together.
            """
            items_str = items_concat.decode().split(self.delim)
            if self.item_class == str:
                return items_str
            else:
                return [ self.item_class(item) for item in items_str ]

        def append(self, txn, bucket_id, item):
            bucket_id_bytes = bytes(bucket_id, encoding='latin-1')
            existing = txn.get(bucket_id_bytes, db=self.db)
            if existing:
                items_concat = bytes(self.delim.join((existing.decode(),
                    str(item))), encoding='latin-1')
            else:
                items_concat = bytes(item, encoding='latin-1')
            txn.put(bucket_id_bytes, items_concat, db=self.db)

        def append_many(self, txn, bucket_id, items):
            bucket_id_bytes = bytes(bucket_id, encoding='latin-1')
            existing = txn.get(bucket_id_bytes, db=self.db)
            if existing:
                items_concat = bytes(self.delim.join((existing.decode(),
                    self.delim.join(items))), encoding='latin-1')
            else:
                items_concat = bytes(self.delim.join(items),
                        encoding='latin-1')
            txn.put(bucket_id_bytes, bytes(items_concat), db=self.db)

    elif sys.version_info.major == 2:

        def iteritems(self, txn):
            """Returns an items iterator."""
            for key, val in iter(txn.cursor(self.db)):
                yield (key, self.convert(val))

        def get(self, txn, bucket_id):
            items_str = txn.get(bucket_id, db=self.db)
            if items_str is None:
                return None
            elif self.item_class == str:
                return items_str.split(self.delim)
            else:
                return [ self.item_class(item) for item in
                        items_str.split(self.delim) ]

        def put(self, txn, bucket_id, items):
            assert type(items) is list or type(items) is tuple
            items_repr = self.delim.join([str(item) for item in items])
            txn.put(bucket_id, items_repr, db=self.db)

        def convert(self, items_concat):
            """
            Args:
                items_concat (str): Items as str repr, concatenated together.
            """
            items_str = items_concat.split(self.delim)
            if self.item_class == str:
                return items_str
            else:
                return [ self.item_class(item) for item in items_str ]

        def append(self, txn, bucket_id, item):
            """Py2 version of append()"""
            existing = txn.get(bucket_id, db=self.db)
            if existing:
                items_concat = self.delim.join((existing, str(item)))
            else:
                items_concat = item
            txn.put(bucket_id, items_concat, db=self.db)

        def append_many(self, txn, bucket_id, items):
            existing = txn.get(bucket_id, db=self.db)
            if existing:
                items_concat = self.delim.join((existing, self.delim.join(items)))
            else:
                items_concat = self.delim.join(items)
            txn.put(bucket_id, items_concat, db=self.db)

class SimpleBucketDict(SimpleBucket):
    def __init__(self, _1=None, _2=None, _3=None):
        self.db = {}
    def iteritems(self, _):
        """Returns an items iterator. (Note: the extra iter() call is necessary
        to make this work in python3.)"""
        return iter(iteritems(self.db))
    def to_dict(self):
        return self.db
    def fp_get(self, _):
        return functools.partial(self.get, _)
    def fp_put(self, _):
        return functools.partial(self.put, _)
    def fp_append(self, _):
        return functools.partial(self.append, _)
    def fp_append_many(self, _):
        return functools.partial(self.append_many, _)
    def get(self, _, bucket_id):
        return self.db.get(bucket_id)
    def put(self, _, bucket_id, items):
        assert type(items) is list or type(items) is tuple
        self.db[bucket_id] = items
    def append(self, _, bucket_id, item):
        self.db.setdefault(bucket_id, [])
        self.db[bucket_id].append(item)
    def append_many(self, _, bucket_id, items):
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

    def __str__(self):
        """String representation of the underlying db. For testing. Produces a
        dictionary-like output, sorted by key."""
        return str(self.db)

    def iteritems(self, txn):
        """Returns an items iterator."""
        return self.db.iteritems(txn)

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

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

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.common import HardClippingNotSupportedException

# Other imports

# For CustomList
import collections

#################
### Functions ###
#################

def to_location_key_no_5p_trim(read_group):
    """Convert a read_group to a location_key that looks like
    'chr5:12345:+,chr5:21111:+'.

    Basically, a double 1-nt entry, representing the soft-clipped-corrected
    start.

    Args:
        read_group (ReadGroup): Create a location key from read_group.
    """

    locs = []
    for read in read_group:
        syn_start, _, _, _ = parse_cigar(read.pos, read.strand, read.cigar)
        locs.append("{}:{}:{}".format(read.rname, syn_start, read.strand))
    return DELIM_BUCKET_LIST.join(locs)

def to_location_key_with_5p_trimming(read_group):
    """Convert a read_group to a location_key that looks like
    'chr5:12345:+,chr5:21111:+'.

    Basically, a double 1-nt entry, representing the soft-clipped-corrected
    and 5'-trimmed-corrected start.

    Args:
        read_group (ReadGroup): Create a location key from read_group.
    """

    # read qnames (and hence 5p trims, etc) are all identical w/in read_group
    # example: D00597:180:C7NMDANXX:6:1101:1184:39633-GGCCTAAT|AGCTCTAG;1,2|3,4
    anno = read_group[0].qname.split(DELIM_ANNO)[1]
    trims = anno.split(DELIM_ANNO_TYPE)[1].split(DELIM_ANNO_READ_PAIR)
    trims_5p = [int(t.split(DELIM_ANNO_ELEMENT)[0]) for t in trims]

    locs = []
    for i, read in enumerate(read_group):
        syn_start, _, _, _ = parse_cigar(read.pos, read.strand, read.cigar)
        if read.strand == '+':
            syn_start_with_5p_trim = syn_start - trims_5p[i%2]
        else:
            syn_start_with_5p_trim = syn_start + trims_5p[i%2]
        locs.append("{}:{}:{}".format(read.rname, syn_start_with_5p_trim, read.strand))
    return DELIM_BUCKET_LIST.join(locs)

def parse_cigar(left, strand, cigar):
    """Parse the CIGAR string, and return the real and synthetic starts/ends,
    where 'synthetic' means that you add on a bit of NTs if there is
    soft-clipping.

    Args:
        left (int): SAM file 'POS' (leftmost alignment)
        strand (str): Forward or reverse strand ('+' or '-').
        cigar (str): CIGAR string.
    Returns:
        (int, int, int, int): 4-tuple: (synthetic_start, start, end,
            synthetic_end), where start/end are beginning and end of alignment
            respectively, and syn_start/syn_end are start/end corrected for
            soft-clipping.
    """
    clipped_left = None
    clipped_right = 0
    num = ''
    align_len = 0

    for c in cigar:
        if c in 'H':
            raise HardClippingNotSupportedException(
                    "SuperDeDuper does not support hard-clipping. "
                    "cigar: {}, left pos: {}, strand: {}".format(cigar, left,
                        strand))
        elif c in 'MIDNSP=X':
            # An operation
            if c == 'S':
                if clipped_left is None:
                    # clipping on left hand side
                    clipped_left = int(num)
                else:
                    # clipping on right hand side
                    clipped_right = int(num)
            elif c in 'M=XDN':
                align_len += int(num)
            elif c in 'IP':
                pass
            else:
                raise
            # Now reset number
            num = ''
            # Additionally, if clipped_left is still None at this point, then
            # the first operation was *not* a left-most soft clipping.  Set it
            # to False to indicate as much, so that if we encounter clipping on
            # the right hand side, it will fail the test 'clipped_left is
            # None', and right side clipping will be correctly recorded.
            if clipped_left is None:
                clipped_left = False
        else:
            # Another number
            num += c

    if clipped_left is None or clipped_left is False:
        clipped_left = 0

    if strand == '+':
        syn_start = left - clipped_left
        start = left
        end = start + align_len - 1
        syn_end = end + clipped_right
    else:
        syn_end = left - clipped_left
        end = left
        start = end + align_len - 1
        syn_start = start + clipped_right

    return (syn_start, start, end, syn_end)


###############
### Classes ###
###############

class Read(object):
    """An alignment line in a SAM file"""
    #_sam_fields = "qname flag rname pos mapq cigar rnext pnext tlen".split()
    _sam_fields = "qname flag rname pos mapq cigar".split()
    __slots__ = _sam_fields

    def __init__(self, line):
        p = line.split('\t')
        self.qname = p[0]
        self.flag  = int(p[1])
        self.rname = p[2]
        self.pos   = int(p[3])
        self.mapq  = p[4]
        self.cigar = p[5]
        # self.rnext = p[6]
        # self.pnext = p[7]
        # self.tlen  = p[8]

    def __repr__(self):
        """Note: This function is used to convert this object to string
        representation when storing entries in LMDB."""
        return DELIM_SAM_FIELD.join((self.qname, str(self.flag), self.rname,
            str(self.pos), self.mapq, self.cigar))

    @property
    def strand(self):
        return '-' if 0x010 == (0x010 & self.flag) else '+'

class CustomList(collections.MutableSequence):
    """Allows effective subclassing of a list."""
    # ABC methods
    def __delitem__(self, key):
        return self._list.__delitem__(key)
    def __getitem__(self, key):
        return self._list.__getitem__(key)
    def __len__(self):
        return self._list.__len__()
    def __setitem__(self, key, value):
        return self.__setitem__(key, value)
    def insert(self, index, obj):
        return self._list.insert(index, obj)

    # Custom methods
    def __init__(self, l=[]):
        self._list = list(l)
    def __repr__(self):
        return self._list.__repr__()

class DupGroup(object):

    def __init__(self):
        self._list = []

    def __iter__(self):
        # Allow iteration over DupGroup
        return iter(self._list)

    def append(self, item):
        self._list.append(item)

class ReadGroup(CustomList):
    __slots__ = 'dataA dataB'.split()

    delim_meta_reads = DELIM_READ_GROUP_METADATA_SAM_RECORDS
    delim_list = DELIM_SAM_LIST_LMDB

    def load(self, obj_bytes):
        """Note: This function is used to convert the string/bytes
        representation of this object in LMDB to an instance of this class.

        Args:
            obj_bytes (str): In-database (e.g. LMDB) representation of the instance.

        Returns:
            ReadGroup: An instance of this class instantiated (a.k.a. loaded)
                from obj_bytes.
        """
        meta_bytes, reads_bytes = obj_bytes.split(
                self.__class__.delim_meta_reads)
        self.dataA, self.dataB = meta_bytes.split(
                self.__class__.delim_list)
        self._list = [ Read(read_bytes) for read_bytes in
                reads_bytes.split(self.__class__.delim_list) ]
        return self

    def __repr__(self):
        """Note: This function is used to convert this object to string
        representation when storing entries in LMDB."""
        meta_bytes = self.__class__.delim_list.join(
                [getattr(self, name, '') for name in self.__slots__])
        reads_bytes = self.__class__.delim_list.join(
                [str(read) for read in self._list])
        return meta_bytes + self.__class__.delim_meta_reads + reads_bytes

    @property
    def reads(self):
        return self._list


# vim: softtabstop=4:shiftwidth=4:expandtab

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

"""Remove PCR duplicates from an alignment file (SAM format).

Usage:
    superdeduper dedup [options] <alignment-file>


Output (subject to change):
    1) ALIGN.sdd.sam - A SAM file with PCR duplicates removed
        from <alignment-file>.
    2) ALIGN.sdd.rejects.sam - A SAM file of PCR duplicates
        removed from <alignment-file>.

Options:
    -h, --help
    -v, --verbose           Be verbose
    -o OUT_DIR              Place results in directory OUT_DIR. Defaults to the
                            current directory.
    -k KIT, --kit KIT       The kit used [default: bioo]. Case insensitive.
    -u, --unpaired          Reads are unpaired [default: False].
    -t N, --threads N       Number of threads.
    -K, --keep-bad-umis     Default is to remove a read (or a read-pair) if
                            there is an error in the read's UMI (or one of the
                            read-pair's UMIs).  Use this flag to retain reads
                            that have an error in their UMIs. Only applicable
                            if --kit bioo.  See also --correct-umis.
    -c, --correct-umis      Perform UMI correction if an UMI is at most 1nt
                            Hamming distance away from at most one known UMI.
                            Only applicable if --kit bioo.  See also
                            --keep-bad-umis. NOT CURRENTLY IMPLEMENTED.
    --store STORE           Storage backend: 'lmdb' or 'memory' [default:
                            memory].
    --no-write-dedupped-sam  Do not write the default output of superdeduper
                             (which is a SAM file with PCR duplicates removed).
                             See also --write-flagged-sam.
    --write-flagged-sam      Write out a SAM file with PCR duplicates included
                             but flagged as PCR duplicates (SAM flag 0x400). See
                             also --no-write-dedupped-sam.
    --no-write-dup-sam       Do no write a SAM file that contains only
                             PCR duplicates.  See also --write-dup-group-file.
    --no-write-dup-group-file  Write a SAM-like file that contains groups of
                               reads (or read-pairs) that have the same location
                               and UMIs.
    --no-write-umi-error-sam  Do not write a SAM file that contains reads or
                              read-pairs with one or more errors in their UMIs.

    --unannotate-read-name   Remove superdeduper read-name annotations from
                             final output.  NOT IMPLEMENTED.

    --random-seed=SEED       For those wanting complete control, change the
                             random seed from its normally hardcoded value.
    --debug-no-build-read-and-loc-dbs   For debugging: Don't build the read and
                                        location DBs.

    --debug-switch S        Fun debug switch [default: nothing].
    --dump-rg-db            Dump the ReadGroup database (for debugging purposes only).
    --dump-loc-db           Dump the Location database (for debugging purposes only).
    --dump-dup-group-db     Dump the Duplication Group database (for debugging purposes only).
    --dump-dup-db           Dump the Duplication database (for debugging purposes only).
    --dump-umi-error-db     Dump the UMI error database (for debugging purposes only).

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

# For iteration
from future.utils import iteritems, itervalues

# For range as iterator in py23
from builtins import range

# SuperDeDuper imports
from superdeduper.constants import *
from superdeduper.common import (setup_report_db, args_to_out_dir, sambamopen,
        filename_in_to_out_sambam, tmpf_start, tmpf_finish, memory_info,
        CannotContinueException)
from superdeduper.db import (ParentDbDict, ParentDbLmdb, SimpleBucketDict,
        SimpleBucketLmdb, SimpleObjectDbDict, SimpleObjectDbLmdb)
from superdeduper.sam import (Read, ReadGroup, to_location_key_with_5p_trimming)
from superdeduper.build_read_and_loc_dbs import write_to_read_and_location_dbs

# debug
from superdeduper.db import LocationBucketDb

# version
try:
    from superdeduper._version import __version__
except ImportError:
    from _version import __version__

## Other imports
from docopt import docopt

# For filename fixing
import os

# For debug timing
import time

# For some printing to stdout
import sys

# For Bioo UMI correction
import distance

# For function partials
import functools

# For choosing by lowest read name the winner/losers
from operator import attrgetter

# For choosing winner of a DupGroup
import random

#################
### Constants ###
#################


#################
### Functions ###
#################

def choose_winner_and_losers_sorted_read_name(fp_get_read_group, dup_group):
    """Given a DupGroup (i.e. a list of read_group_ids), chooses as the winner
    the first by alphanumeric sort.

    Args:
        fp_get_read_group ((Transaction, str) -> ReadGroup): Function pointer
            that retrieves a ReadGroup from the read_group_db when passed a
            read_group_id.
        dup_group (DupGroup): A DupGroup filled up with ReadGroups.

    Returns:
        (str, (str,)): A two tuple: First member is the winning read_group_id,
            second member is a list of the losing read_group_ids.
    """

    dup_group = (fp_get_read_group(rg_id) for rg_id in dup_group)
    dup_group = sorted(dup_group, key=attrgetter('name'))
    winner = dup_group[0]
    losers = dup_group[1:]
    return (winner, losers)

def choose_winner_and_losers_longest_highest_quality(fp_get_read_group, dup_group):
    # TODO: Question, catherine, which to prioritize? Length or quality?

    # Note: To do this would cost more.  We're not currently storing average
    # quality score or the QUAL field in the read_group_db, so presumably we'd
    # have to calculate this upon reading the input SAM file, and store it
    # (without messing up the currently repr/load semantics). (Nor the length
    # of the sequence, but that's available via parse_cigar). Certainly
    # do-able, but I'm happy with the lack of bias provided by
    # choose_winner_losers_random_fixed_seed.
    pass

def choose_winner_and_losers_random_fixed_seed(fp_get_read_group, dup_group):
    """Given a DupGroup (i.e. a list of read_group_ids), chooses a random
    winner.  The random seed is fixed at the beginning of dedup.

    Args:
        fp_get_read_group ((Transaction, str) -> ReadGroup): Function pointer
            that retrieves a ReadGroup from the read_group_db when passed a
            read_group_id.
        dup_group ([str]): A list of read_group_ids representing from one
            DupGroup.

    Returns:
        (str, (str,)): A two tuple: First member is the winning read_group_id,
            second member is a list of the losing read_group_ids.
    """
    # Convert dup_group to a list (generator) of its member ReadGroups.
    dup_group = sorted((fp_get_read_group(rg_id) for rg_id in dup_group))
    # Choose a winner randomly
    winner_idx = random.randrange(0, len(dup_group))
    winner = dup_group.pop(winner_idx)
    losers = dup_group
    return (winner, losers)

def log_winner_losers(winner, losers):
    """Logs winner and losers, somehow.  For now, just printing...
    """
    pass

def umi_bioo_report(seq_umi):
    """Generates a 'report' about a given sequenced UMI. It finds the Bioo UMIs
    closest in Hamming distance to the sequenced_umi.  It reports that Hamming
    distance along with all of the Bioo UMIs that distance away from the
    sequenced_umi.

    Args:
        seq_umi (str): The uncorrected UMI from the read sequence.
    Returns:
        (int, [str]): The report, a two-tuple.  First member of the tuple is
            the Hamming distance, second member is all the Bioo UMIs that
            distance away.
    """
    dist = inf = 999
    potential_umis = []

    if seq_umi in UMIS_BIOO:
        potential_umis = [seq_umi]
        dist = 0
    else:
        potential_umis = []
        for curr_dist in range(1,9):
            for umi in UMIS_BIOO:
                d = distance.hamming(umi, seq_umi)
                if d == curr_dist:
                    potential_umis.append(umi)
                    dist = curr_dist
            if dist < inf:
                # Found at least one
                break

    if dist == inf:
        # TODO: Remove this code if not found after this...
        # Hrm, fixed the bug above (range(1,9) was previously range(1,8)) so
        # being here should be impossible.  Announce anomoly.
        msg = "WARNING umi_bio_report: dist == infinity, seq_umi = {}".format(
                    seq_umi)
        sys.stderr.write(msg)

    return (dist, potential_umis)

def process_location_pe_bioo_1nt(report_db, umi_error_db, reject_umi_errors,
        correct_umis, read_groups):
    """Does many things:

        * Partitions ReadGroups at this location into DupGroups (one DupGroup
          per umi-pair).
        * Identifies ReadGroups which have one or more errors in their UMIs,
          and writes those to the umi_error_db (eventually these are used to
          write out superdeduper SAM TAGs, just for reads with UMI errors).
        * Optionally conservatively corrects UMIs with errors (1nt away from
          exactly one known UMI) (Actuall, not implemented at this time!)
        * Updates report_db for several metrics (what catherine wanted, and
            more):
                - levels of duplications (how many found)
                - number of duplicates we would have thrown out if not for UMIs.
                - number of ReadGroups rejected due to errors in UMIs.
                - more not listed here.

    This is the paired-end Bioo version of the family of identify_dup_groups().

    Args:
        report_db (dict): A database for metrics to report.
        reject_umi_errors (bool): Whether or not to reject the umis with errors.
        umi_error_db (dict): DB of read groups with one or more UMI errors.
        correct_umis (bool): Whether or not to correct the umis.
        read_groups (dict(str) -> [ReadGroup]): Dictionary, key: read_group_id,
            val: list of read_groups.
    Returns:
        [[str]]: A list of lists of ReadGroup ids.  Each inner list of
            ReadGroup ids constitutes a DupGroup.

    Superdeduper SAM TAGS

        'sam_tags' is a tab separated list of superdeduper-defined SAM TAGs. It's
        in flux right now.  Here's the current specification.

        Superdeduper SAM file TAGs specification:

            NOTE! SUBJECT TO CHANGE!!!

            d1:i:count      Read1's UMI is 'count' nts hamming distance from a
                            known UMI.
            d2:i:count      Same as d1 but for Read2.
            n1:i:count      Read1's UMI is closest to 'count' known UMIs.
            n2:i:count      Same as n1, but for Read2.
            c1:Z:nts        There is only one case where a sequenced UMI might get
                            corrected (1nt away from just one known UMI).  IF we
                            end up doing this type of correction, then the
                            corrected UMI used will be 'nts', and only the read
                            that got corrected will get this TAG.
                            (Note: Uncorrected UMI is in the annotated read name.)
            c2:Z:nts        Same as c1, but for Read2.
    """
    # key: umi_pair, val: list of read_group_ids with that umi_pair in the form
    #                     of a (read_group_id, read_group) tuple
    rg_ids_by_umi_pair = {}

    for read_group_id, read_group in iteritems(read_groups):

        # Note: This won't support multi-mapped alignments like other parts of
        # the code do...

        ## Pull out the UMIs and examine them.

        # D00597:180:C7NMDANXX:6:1101:1184:39633-GGCCTAAT^AGCTCTAG;2^0
        anno = read_group[0].qname.split(DELIM_ANNO)[1]
        # GGCCTAAT^AGCTCTAG;2^0
        umis = anno.split(DELIM_ANNO_TYPE)[0]
        # GGCCTAAT^AGCTCTAG
        umi1, umi2 = umis.split(DELIM_ANNO_READ_PAIR)
        # [GGCCTAAT, AGCTCTAG]
        dist1, potential_umis1 = umi_bioo_report(umi1)
        dist2, potential_umis2 = umi_bioo_report(umi2)
        len_potential_umis1 = len(potential_umis1)
        len_potential_umis2 = len(potential_umis2)

        ## Add superdeduper SAM TAGs and optionally correct UMIs.
        if dist1 >= 1 or dist2 >= 1:
            # Found UMI error!

            sam_tags1 = "{}{}\t{}{}".format(
                     SAM_TAG_READ1_HAMMING_DIST_UMI, dist1,
                     SAM_TAG_READ1_NUM_CLOSEST_UMIS, len_potential_umis1)
            sam_tags2 = "{}{}\t{}{}".format(
                     SAM_TAG_READ2_HAMMING_DIST_UMI, dist2,
                     SAM_TAG_READ2_NUM_CLOSEST_UMIS, len_potential_umis2)
            # Could we have corrected?
            if (    dist1 <= 1 and len_potential_umis1 <= 1 and
                    dist2 <= 1 and len_potential_umis2 <= 1):
                # Yes, we could have. Annotate.
                if dist1 == 1 and len_potential_umis1 == 1:
                    sam_tags1 += '\t{}{}'.format(SAM_TAG_READ1_CLOSEST_UMI,
                            potential_umis1[0])
                    if correct_umis:
                        # CORRECT UMI1!
                        umi1 = potential_umis1[0]
                if dist2 == 1 and len_potential_umis2 == 1:
                    sam_tags2 += '\t{}{}'.format(SAM_TAG_READ2_CLOSEST_UMI,
                            potential_umis2[0])
                    if correct_umis:
                        # CORRECT UMI2!
                        umi2 = potential_umis2[0]

            # Write to the umi_error_db:
            # NOTE: Assumption: The umi_error_db will be small, so just using a
            # simple dict here...
            umi_error_db[read_group.name] = (sam_tags1, sam_tags2)

            # report_db: count of UMI errors (largest dist only reported)
            dist = dist1 if dist1 > dist2 else dist2
            metric = "{}{}".format(LOG_NUM_READ_GROUPS_WITH_UMI_ERROR_DIST,
                    dist)
            report_db[metric] += 1
            # report_db: total number of read_groups with UMI errors
            report_db[LOG_NUM_READ_GROUPS_WITH_UMI_ERROR] += 1


        if reject_umi_errors and (dist1 >= 1 or dist2 >= 1):
            ## User requested rejection of ReadGroups with UMI errors.

            # report_db: count of rejects due to UMI errors
            dist = dist1 if dist1 > dist2 else dist2
            metric = "{}{}".format(LOG_NUM_READ_GROUPS_REJECTED_DUE_TO_UMI_ERROR_DIST,
                    dist)
            report_db[metric] += 1

        else:
            ## User requested keep all ReadGroups (even those with UMI errors).

            umi_pair = ",".join([umi1, umi2])
            rg_ids_by_umi_pair.setdefault(umi_pair, [])
            rg_ids_by_umi_pair[umi_pair].append(read_group_id)

    ## Finalize DupGroups
    dup_groups = rg_ids_by_umi_pair.values()

    # report_db: update number of unique location/umi_pair combinations
    # There is another place in write_to_dup_group_db where this metric is
    # incrememted.
    report_db[LOG_NUM_UNIQUE_UMI_PAIR_LOCATION_COMBINATIONS] += len(dup_groups)

    # Only DupGroups with more than one member are real DupGroups.
    dup_groups_larger_than_one_member = [ dg for dg in dup_groups if len(dg) > 1 ]

    # report_db: log number of true DupGroups:
    report_db[LOG_NUM_DUP_GROUPS] += len(dup_groups_larger_than_one_member)

    return dup_groups_larger_than_one_member

def put_dup_groups(dup_group_db, dup_groups):
    """For each duplicate group, given a duplicate group (in the form of a list
    of read_group_ids), write that duplicate group to the DupGroupDB, using
    either an existing DupGroup or creating a new one.

    Args:
        dup_group_db (DB): The DupGroup database.
        dup_groups ([[str]]): A list of lists of ReadGroup ids.  Each list of
            ReadGroup ids is a "DupGroup" (i.e. a Duplicate Group).

    The end result might look something like this:
        For these two dup groups:
            (1,2,3) and (4,5)
        You would end up with two total DupGroup objects, in the
        DupGroupDB (dgdb) like so:
            dgdb[1] -> DupGroupObjectA
            dgdb[2] -> DupGroupObjectA
            dgdb[3] -> DupGroupObjectA
            dgdb[4] -> DupGroupObjectB
            dgdb[5] -> DupGroupObjectB
    """

    for dup_group in dup_groups:

        # Is there any existing DupGroup for any of our ReadGroups?
        existing = set([ dup_group_db[rg_id] for rg_id in dup_group if rg_id in
                dup_group_db ])
        if len(existing) > 1:
            raise(CannotContinueException,
                    "Found more than one DupGroup representing: {}".format(
                        existing))
        elif len(existing) == 1:
            # Found an existing DupGroup, use that one
            dup_group_obj = existing[0]
        else:
            dup_group_obj = DupGroup()

        for read_group_id in dup_group:
            dup_group_obj.add(read_group_id)
            dup_group_db[read_group_id] = dup_group_obj

def write_to_dup_group_db(report_db, parent_db, read_group_db, loc_db,
        dup_group_db, records_per_txn, fp_process_location):
    """
    Arguments:
        fp_process_location (function): Function that does a lot of stuff, but
            mainly, processes a given location, partitioning ReadGroups at that
            location into DupGroups (by umi-pair), optionally rejects and/or
            corrects UMIs, logs things, etc.
    """

    # Populate the DupGroupDB
    with parent_db.begin(True) as txn_loc:

        fp_get_read_group = read_group_db.fp_get(txn_loc)
        # fp_put_read_group = read_group_db.fp_put(txn_loc)

        for location_key, read_group_ids in loc_db.iteritems(txn_loc):
            # record another location
            report_db[LOG_NUM_LOCATIONS] += 1
            if len(read_group_ids) > 1:
                # Found a location with more than one ReadGroup, potential
                # duplicate. Build a local dict of just the read_groups found
                # at this location
                read_groups = {}
                for read_group_id in read_group_ids:
                    read_group = fp_get_read_group(read_group_id)
                    read_groups[read_group_id] = read_group
                # Identify DupGroups and Rejected ReadGroups (rejected due to
                # errors in UMIs)
                dup_groups = fp_process_location(read_groups)
                # Write to the DupGroupDb
                put_dup_groups(dup_group_db, dup_groups)
            else:
                # Only one read group at this location, therefore increment the
                # number of unique location/umi_pair combos.  (When there are
                # more than one read_groups per location, this metric is
                # updated in process_location() (see a few lines above))
                metric = LOG_NUM_UNIQUE_UMI_PAIR_LOCATION_COMBINATIONS
                report_db[metric] += 1

def write_to_dup_db(report_db, parent_db, read_group_db, dup_group_db, dup_db,
        records_per_txn, fp_choose_winner_and_losers, fp_log_winner_losers):
    """
    Args:
        fp_choose_winner_and_losers (function): Function that determines
            which ReadGroup of a DupGroup is kept.
    """

    # NOTE! report_db not currently being used here?

    first_loop = True
    done = False
    time1 = None
    time2 = None
    time_in_write_db = 0

    # Grab a unique list of DupGroups
    # TODO: potentially expensive? measure...
    dg_ids = {}
    dup_groups = []
    for dup_group in itervalues(dup_group_db):
        if id(dup_group) not in dg_ids:
            dg_ids[id(dup_group)] = True
            dup_groups.append(dup_group)
    dup_groups = sorted(dup_groups)

    # Create an items iterator for the DupGroups
    iter_dup_group = iter(dup_groups)

    # Populate the DupDB
    while (not done):
        if first_loop:
            first_loop = False
        else:
            time2 = time.time()
            time_in_write_db += (time2 - time1)
            print("Commit dup_group_db at record_count = {}, time taken = {}, current mem MBs: {}".format(
                record_count, time2 - time1, memory_info(True)))
        time1 = time.time()
        with parent_db.begin(True) as txn_dup:
            # sys.stdout.write("Begin commit to DupDB... ")
            # functions
            fp_get_read_group = read_group_db.fp_get(txn_dup)
            fp_put_dup_db = dup_db.fp_put(txn_dup)
            fp_choose_winner_and_losers2 = functools.partial(
                    fp_choose_winner_and_losers, fp_get_read_group)
            (done, record_count) = write_to_dup_db_txn(iter_dup_group,
                    records_per_txn, fp_put_dup_db,
                    fp_choose_winner_and_losers2, fp_log_winner_losers)

def write_to_dup_db_txn(iter_dup_group, records_per_txn, fp_put_dup_db,
        fp_choose_winner_and_losers, fp_log_winner_losers):
    """Write a 'records_per_txn' number of to DB.

    Args:
        iter_dup_group (variable): An items iterator for the set of DupGroups.
        records_per_txn (int): The number of records.
        fp_choose_winner_and_losers (function): Function to ...
    Returns:
        (bool, int): 2-tuple with elements a) done or not, b) current
            record count.
    """
    record_count = 0
    curr_dup_group = None
    done = False

    try:
        while record_count < records_per_txn:
            curr_dup_group = next(iter_dup_group)
            winner, losers = fp_choose_winner_and_losers(curr_dup_group)
            for loser in losers:
                fp_put_dup_db(loser.name, [''])
            fp_log_winner_losers(winner, losers)
            record_count += 1
    except(StopIteration):
        done = True
    return(done, record_count)

def write_dup_group_sam_like_file(parent_db, read_group_db, dup_group_db,
        dup_group_sam_like):
    """Writes a "DupGroup" SAM-like file - Similar to a SAM file; the
    ReadGroups from a DupGroup are printed together; each DupGroup is separated
    from other DupGroups by new lines."""

    ## Write only the dup_group_sam_like file.
    with parent_db.begin(False) as txn, \
            open(dup_group_sam_like, 'w') as f_dup_group_sam_like:

        fp_get_read_group = read_group_db.fp_get(txn)

        # TODO: Potentially expensive?  And you've already generated this
        # earlier...
        # Grab a unique list of DupGroups
        time1 = time.time()
        dg_ids = {}
        dup_groups = []
        for dup_group in itervalues(dup_group_db):
            if id(dup_group) not in dg_ids:
                dg_ids[id(dup_group)] = True
                dup_groups.append(dup_group)
        dup_groups = sorted(dup_groups)
        time2 = time.time()
        print('DEBUG TIMING A: It took {}s to generate list of unique dup groups.'.format(
                time2 - time1))

        for dup_group in dup_groups:
            for read_group_id in dup_group:
                read_group = fp_get_read_group(read_group_id)
                for read in read_group:
                    f_dup_group_sam_like.write(repr(read))
                    f_dup_group_sam_like.write('\n')
            # This newline separates each dup_group from the next
            f_dup_group_sam_like.write('\n\n')

def write_output_files_pe(parent_db, read_group_db, dup_db, umi_error_db,
        input_file, reject_umi_errors, dedupped_sam, flagged_sam, dup_only_sam,
        rejects_sam, write_dedupped_sam, write_flagged_sam, write_dup_only_sam,
        write_dup_group_sam_like, write_umi_error_rejects):
    """Writes the output files for paired-end input. Including:
        * A dedupped SAM file - no PCR duplicates included
        * A flagged SAM file - Identical to the input_file, but with PCR
            duplicates flagged.
        * A dup-only SAM file - Only contains the PCR duplicates.
        * A umi-error-rejects file. - Reads rejected due to error in UMI.
    """
    ## Write everything except the dup_group_sam_like file.
    with parent_db.begin(False) as txn, \
            sambamopen(input_file) as fin, \
            open(dedupped_sam, 'w') as f_dedupped_sam, \
            open(flagged_sam, 'w') as f_flagged_sam, \
            open(dup_only_sam, 'w') as f_dup_only_sam, \
            open(rejects_sam, 'w') as f_umi_reject_sam:

        # Setup
        fp_get_dup = dup_db.fp_get(txn)
        aln_lines = []
        group_count = 0
        total_count = 0
        remaining_lines = True
        aln_line = None
        prev_qname = None

        # Write out headers
        while True:
            aln_line = fin.readline()
            if aln_line[0] == '@':
                f_dedupped_sam.write(aln_line)
                f_flagged_sam.write(aln_line)
                f_dup_only_sam.write(aln_line)
                f_umi_reject_sam.write(aln_line)

                if aln_line[0:3] == '@HD':
                    # Already wrote the first line (header line), now we can write
                    # our @PG line.
                    pg_line = '@PG\tID:{}\tPN:{}\tVN:v{}\tCL:{}\n'.format(
                            'superdeduper', 'superdeduper', __version__,
                            ' '.join(sys.argv))
                    f_dedupped_sam.write(pg_line)
                    f_flagged_sam.write(pg_line)
                    f_dup_only_sam.write(pg_line)
                    f_umi_reject_sam.write(pg_line)
            else:
                prev_qname, _ = aln_line.split('\t', 1)
                aln_lines.append(aln_line)
                break

        ## Write out alignment lines
        while remaining_lines:
            # Outer loop: Just keep going until EOF.
            while True:
                # Inner loop: Collect all alignments with same QNAME.
                total_count += 1
                aln_line = fin.readline()
                if not aln_line:
                    # EOF
                    qname = None
                    remaining_lines = False
                    break
                qname, _ = aln_line.split('\t', 1)

                if prev_qname and prev_qname != qname:
                    # New qname found, write out!
                    break
                else:
                    aln_lines.append(aln_line)
                    prev_qname = qname

            ## Have a group of alignment lines with same QNAME, write to files.

            # First, add superdeduper SAM TAGs if its in the umi_error_db
            if prev_qname in umi_error_db:
                # Error in UMI, add sdd-specific umi error tags.
                new_aln_lines = []
                for i, line in enumerate(aln_lines):
                    # Update the alignment line with sam tags
                    line_with_sam_tags = '\t'.join(
                            (aln_lines[i].rstrip(), umi_error_db[prev_qname][i]))
                    line_with_sam_tags += '\n'
                    new_aln_lines.append(line_with_sam_tags)
                aln_lines = new_aln_lines

            # Now write files
            if fp_get_dup(prev_qname):
                # Found a duplicate.
                # Update flag field to indicate its a dup.
                # Write updated line to dup_only and flagged_sam files.
                for line in aln_lines:
                    # recall FLAG is the second field in sam files
                    parts = line.split('\t', 2)
                    parts[1] = str(int(parts[1]) | SAM_FORMAT_FLAG_DUPLICATE)
                    flagged_line = '\t'.join(parts)
                    f_flagged_sam.write(flagged_line)
                    f_dup_only_sam.write(flagged_line)
            elif prev_qname in umi_error_db and reject_umi_errors:
                # Error in UMI and no rejects wanted by user: write to umi_reject file
                for line in aln_lines:
                    f_umi_reject_sam.write(line)
            else:
                # No duplicate: write to dedupped and flagged files
                for line in aln_lines:
                    f_dedupped_sam.write(line)
                    f_flagged_sam.write(line)

            # Prep for next round
            prev_qname = qname
            aln_lines = [aln_line]
            group_count += 1

def parse_args(args):
    """Parse the command line arguments."""

    debug_switch = args['--debug-switch']
    dump_rg_db = args['--dump-rg-db']
    dump_loc_db = args['--dump-loc-db']
    dump_dup_group_db = args['--dump-dup-group-db']
    dump_dup_db = args['--dump-dup-db']
    dump_umi_error_db = args['--dump-umi-error-db']

    random_seed = args['--random-seed']

    write_dedupped_sam = not args['--no-write-dedupped-sam']
    write_flagged_sam = args['--write-flagged-sam']
    write_dup_only_sam = not args['--no-write-dup-sam']
    write_dup_group_sam_like = not args['--no-write-dup-group-file']
    write_umi_error_rejects = not args['--no-write-umi-error-sam']

    # Convert ~ to real path
    input_file = os.path.expanduser(args['<alignment-file>'])

    # Which kit?
    kit = args['--kit'].lower()
    if kit == KIT_BIOO:
        pass
    else:
        raise CannotContinueException("""Kit {} is not supported.""".format(kit))

    if kit != KIT_BIOO and write_umi_error_rejects:
        raise CannotContinueException(
                "Cannot identify UMI errors when kit is {}.".format(kit))

    paired = False if args['--unpaired'] else True
    reject_umi_errors = not args['--keep-bad-umis']
    correct_umis = args['--correct-umis']
    build_read_and_loc_dbs = not args['--debug-no-build-read-and-loc-dbs']

    if correct_umis and kit != KIT_BIOO:
        raise CannotContinueException(
                """Cannot correct UMIs when kit is not Bioo.""")

    if reject_umi_errors and correct_umis:
        raise CannotContinueException(
                "Doesn't make sense to reject and *also* correct erroneous UMIs!!"
                " If passing --correct, you must also pass --keep-bad-umis.")

    # Figure out which function to use to write to output file.
    num_threads = args['--threads']

    # Which store to use
    if args['--store'] not in (STORE_OPTION_LMDB, STORE_OPTION_MEMORY):
        raise CannotContinueException("""Store {} is not supported.""".format(args['--store']))
    store = args['--store']

    outdir = args_to_out_dir(args)

    return (kit, store, outdir, input_file, paired, build_read_and_loc_dbs,
            reject_umi_errors, correct_umis, write_dedupped_sam,
            write_flagged_sam, write_dup_only_sam, write_dup_group_sam_like,
            write_umi_error_rejects, random_seed, debug_switch, dump_rg_db,
            dump_loc_db, dump_dup_group_db, dump_dup_db, dump_umi_error_db)

def run(kit, store, outdir, input_file, paired, build_read_and_loc_dbs,
        reject_umi_errors, correct_umis, write_dedupped_sam, write_flagged_sam,
        write_dup_only_sam, write_dup_group_sam_like,
        write_umi_error_rejects, random_seed, debug_switch, dump_rg_db,
        dump_loc_db, dump_dup_group_db, dump_dup_db, dump_umi_error_db):
    """Start the run.

    Args:
        kit (str): kit...
        store (str): Which storage backend to use.
        outdir (str): Output directory for results
        input_dir (str): ...
        build_read_and_loc_dbs (bool): Whether or not to build the
            read_group_db and location_db.
    """
    ## Set the random seed (if not set by user).
    random.seed(RANDOM_SEED if random_seed is None else random_seed)

    # report_db:
    #   A regular 'dict'.
    #   key: string describing a given (count) metric (I think they're all counts)
    #   val: (int) a count
    #   purpose: To provide a report at the end of the day on various metrics
    #       collected.
    # umi_error_db:
    #   A regular 'dict'.
    #   key: (str) A ReadGroup name.
    #   val: Not used (just doing 'True')
    #   purpose: To keep track of which reads have errors in one or more of
    #       their UMIs (and may optionally be rejected outright).
    # dup_group_db:
    #   A regular 'dict'.
    #   key: read_group_id
    #   val: list of read_group_ids that are duplicates of read_group_id
    #   purpose: To store stats, generate logs, debugging, etc. Maybe to
    #       also choose which duplicate to use.
    # dup_db:
    #   A SimpleBucketDB.
    #   key: ReadName of a PCR duplicate to be removed.
    #   val: Always just "True"
    #   purpose: When walking over the SAM/BAM file during last pass, any
    #       ReadName found in this DB will be removed from the final output.

    ## Setup databases
    report_db = setup_report_db()
    umi_error_db = {}
    dup_group_db = {}
    if store == STORE_OPTION_LMDB:
        db_file = os.path.join(outdir, os.path.split(input_file)[1] + '.sdd.db')
        parent_db = ParentDbLmdb(db_file, LMDB_MAX_DBS, LMDB_DB_SIZE)
        read_group_db = SimpleObjectDbLmdb('read_group', parent_db, parent_db.env, ReadGroup)
        location_bucket_store = SimpleBucketLmdb('location_bucket_store',
                parent_db, parent_db.env, DELIM_BUCKET_LIST, str)
        dup_db = SimpleBucketLmdb('duplicate', parent_db, parent_db.env,
                DELIM_BUCKET_LIST, str)
    elif store == STORE_OPTION_MEMORY:
        parent_db = ParentDbDict()
        read_group_db = SimpleObjectDbDict()
        location_bucket_store = SimpleBucketDict()
        dup_db = SimpleBucketDict()
    loc_db = LocationBucketDb(location_bucket_store, to_location_key_with_5p_trimming)

    ## What fp_process_location() and write_output_files() to use?
    if kit == KIT_BIOO:
        if paired:
            # TODO: HARDCODED for now. Add command line switches for doug seq later.
            fp_process_location = functools.partial(
                    process_location_pe_bioo_1nt, report_db,
                    umi_error_db, reject_umi_errors, correct_umis)
            fp_write_output_files = write_output_files_pe
        else:
            raise CannotContinueException("""Doesn't support single-end yet.""")
            # TODO: HARDCODED for now. Add command line switches for doug seq later.
            fp_process_location = functools.partial(
                    process_location_sr_bioo_1nt, report_db,
                    umi_error_db, reject_umi_errors, correct_umis)
            fp_write_output_files = write_output_files_sr
    else:
        raise CannotContinueException("""Kit {} is not supported.""".format(kit))

    ## Winners and Losers
    # TODO: HARDCODED for now.
    fp_choose_winner_and_losers = choose_winner_and_losers_random_fixed_seed
    fp_log_winner_losers = log_winner_losers

    ## Setup output filenames
    # TODO: Offer BAM output?
    if write_dedupped_sam:
        dedupped_sam = filename_in_to_out_sambam(input_file,
                'dups_removed.sam', outdir)
    else:
        dedupped_sam = os.devnull
    if write_flagged_sam:
        flagged_sam = filename_in_to_out_sambam(input_file,
                'dups_flagged.sam', outdir)
    else:
        flagged_sam = os.devnull
    if write_dup_only_sam:
        dup_only_sam = filename_in_to_out_sambam(input_file,
                'duplicates.sam', outdir)
    else:
        dup_only_sam = os.devnull
    if write_dup_group_sam_like:
        dup_group_sam_like = filename_in_to_out_sambam(input_file,
                'dup_groups.samlike', outdir)
    else:
        dup_group_sam_like = os.devnull
    if write_umi_error_rejects:
        rejects_sam = filename_in_to_out_sambam(input_file,
                'umi_errors.sam', outdir)
    else:
        rejects_sam = os.devnull

    ### Go ###


    if build_read_and_loc_dbs:
        time1 = time.time()
        with sambamopen(input_file) as fin:

            ## First op, build read and location dbs
            write_to_read_and_location_dbs(report_db, fin, parent_db,
                    read_group_db, loc_db, RECORDS_PER_TXN)
        time2 = time.time()
        print("Building read_group_db and loc_db took: {}s, current mem (MBs): {}".format(
            time2 - time1, memory_info(True)))

    ## Second op, build DupGroupDB
    time1 = time.time()
    write_to_dup_group_db(report_db, parent_db, read_group_db, loc_db,
            dup_group_db, RECORDS_PER_TXN, fp_process_location)
    time2 = time.time()
    print("Building dup_group_db took: {}s, current mem (MBs): {}".format(
        time2 - time1, memory_info(True)))

    # Third op, resolve duplicates and build DupDB
    time1 = time.time()
    random.seed(RANDOM_SEED)
    write_to_dup_db(report_db, parent_db, read_group_db, dup_group_db, dup_db,
            RECORDS_PER_TXN, fp_choose_winner_and_losers,
            fp_log_winner_losers)
    time2 = time.time()
    print("Building dup_db took: {}s, current mem (MBs): {}".format(
        time2 - time1, memory_info(True)))

    ## Setup tmp filenames (now that most of the work is complete)
    out_files = [dedupped_sam, flagged_sam, dup_only_sam, dup_group_sam_like,
            rejects_sam]
    (tmp_dedupped_sam, tmp_flagged_sam, tmp_dup_only_sam,
            tmp_dup_group_sam_like, tmp_rejects_sam) = tmpf_start(*out_files)

    ## Fourth op: Write the dup_group_sam_like file
    time1 = time.time()
    write_dup_group_sam_like_file(parent_db, read_group_db, dup_group_db,
            tmp_dup_group_sam_like)
    time2 = time.time()
    print("Writing DupGroup file took: {}s, current mem (MBs): {}".format(
        time2 - time1, memory_info(True)))

    ## Fifth op: Walk through SAM/BAM input_file and write output files.
    time1 = time.time()
    fp_write_output_files(parent_db, read_group_db, dup_db, umi_error_db,
            input_file, reject_umi_errors, tmp_dedupped_sam, tmp_flagged_sam,
            tmp_dup_only_sam, tmp_rejects_sam, write_dedupped_sam,
            write_flagged_sam, write_dup_only_sam, write_dup_group_sam_like,
            write_umi_error_rejects)
    time2 = time.time()
    print("Writing output files took: {}s, current mem (MBs): {}".format(
        time2 - time1, memory_info(True)))

    # Write report_db
    for k,v in sorted(iteritems(report_db)):
        print("{}: {}".format(k,v))

    # Finish temp files
    tmpf_finish(tmp_dedupped_sam, tmp_flagged_sam, tmp_dup_only_sam,
            tmp_dup_group_sam_like, tmp_rejects_sam)

    # TEMPORARY!  Just for bootstrapping the testing of dedup. Will change to
    if dump_rg_db:
        sys.stderr.write(str(read_group_db))
        sys.stderr.write('\n')
    if dump_loc_db:
        sys.stderr.write(str(loc_db))
        sys.stderr.write('\n')
    if dump_dup_group_db:
        sys.stderr.write(str(dup_group_db))
        sys.stderr.write('\n')
    if dump_dup_db:
        sys.stderr.write(str(dup_db))
        sys.stderr.write('\n')
    if dump_umi_error_db:
        sys.stderr.write(str(umi_error_db))
        sys.stderr.write('\n')

    return out_files


###############
### Classes ###
###############

class DupGroup(set):
    """When completely built, represents a set of read_groups at one
    genomic location (technically at one location_key) that share the same UMI
    or UMIs.

    For example, for paired-end sequencing, to place two read-pairs in the same
    DupGroup, R1 and R2 from each read-pair would need to have the same
    synthetic_start (e.g. both read pairs have location_key
    'chr5:1000000:+,chr5:1000500:-') (or, in the future, possibly extend this)
    as well as share the same umi-pair (e.g. both R1s have ACGTACGT and both
    R2s have umi TTGGCCAA).

    Yup, DupGroup is just a set.
    """
    pass


############
### Main ###
############

def main():
    args = docopt(__doc__)
    run(*parse_args(args))

# vim: softtabstop=4:shiftwidth=4:expandtab
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

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# NOTE: Do *not* do the following:
# from builtins import str
# from builtins import chr
# py-lmdb uses bytes() for py3 and str() for py2.
# Doing any of the above starts turning things into unicode.  We want native
# strings.

################
### Defaults ###
################

# The configuration file
DEFAULT_DUPLIGANGER_CONFIG_FILE =                    "dupliganger.config"

#################
### Constants ###
#################

# Bioo kit name
KIT_BIOO =                                                           'bioo'

# Bioo UMIs
UMIS_BIOO = ['AACGCCAT', 'AAGGTACG', 'AATTCCGG', 'ACACAGAG', 'ACACTCAG',
        'ACACTGTG', 'ACAGGACA', 'ACCTGTAG', 'ACGAAGGT', 'ACGACTTG', 'ACGTCAAC',
        'ACGTCATG', 'ACTGTCAG', 'ACTGTGAC', 'AGACACTC', 'AGAGGAGA', 'AGCATCGT',
        'AGCATGGA', 'AGCTACCA', 'AGCTCTAG', 'AGGACAAC', 'AGGACATG', 'AGGTTGCT',
        'AGTCGAGA', 'AGTGCTGT', 'ATAAGCGG', 'ATCCATGG', 'ATCGAACC', 'ATCGCGTA',
        'ATCGTTGG', 'CAACGATC', 'CAACGTTG', 'CAACTGGT', 'CAAGTCGT', 'CACACACA',
        'CAGTACTG', 'CATCAGCA', 'CATCGTTC', 'CCAAGGTT', 'CCTAGCTT', 'CGATTACG',
        'CGCCTATT', 'CGTTCCAT', 'CGTTGGAT', 'CTACGTTC', 'CTACTCGT', 'CTAGAGGA',
        'CTAGGAAG', 'CTAGGTAC', 'CTCAGTCT', 'CTGACTGA', 'CTGAGTGT', 'CTGATGTG',
        'CTGTTCAC', 'CTTCGTTG', 'GAACAGGT', 'GAAGACCA', 'GAAGTGCA', 'GACATGAG',
        'GAGAAGAG', 'GAGAAGTC', 'GATCCTAG', 'GATGTCGT', 'GCCGATAT', 'GCCGATTA',
        'GCGGTATT', 'GGAATTGG', 'GGATAACG', 'GGCCTAAT', 'GGCGTATT', 'GTCTTGTC',
        'GTGATGAG', 'GTGATGTC', 'GTGTACTG', 'GTGTAGTC', 'GTTCACCT', 'GTTCTGCT',
        'GTTGTCGA', 'TACGAACC', 'TAGCAAGG', 'TAGCTAGC', 'TAGGTTCG', 'TATAGCGC',
        'TCAGGACT', 'TCCACATC', 'TCGACTTC', 'TCGTAGGT', 'TCGTCATC', 'TGAGACTC',
        'TGAGAGTG', 'TGAGTGAG', 'TGCTTGGA', 'TGGAGTAG', 'TGTGTGTG', 'TTCGCCTA',
        'TTCGTTCG']

# Dupligänger defined SAM TAGs
SAM_TAG_READ1_HAMMING_DIST_UMI =                                    'd1:i:'
SAM_TAG_READ2_HAMMING_DIST_UMI =                                    'd2:i:'
SAM_TAG_READ1_NUM_CLOSEST_UMIS =                                    'n1:i:'
SAM_TAG_READ2_NUM_CLOSEST_UMIS =                                    'n2:i:'
SAM_TAG_READ1_CLOSEST_UMI      =                                    'c1:i:'
SAM_TAG_READ2_CLOSEST_UMI      =                                    'c2:i:'

# ReportDB metrics

LOG_NUM_LOCATIONS =                                         'num_locations'
LOG_NUM_UNIQUE_UMI_AND_LOCATION_COMBINATIONS = (
                                 'num_unique_umi_and_location_combinations')
LOG_NUM_READ_GROUPS =                                     'num_read_groups'
LOG_NUM_DUP_GROUPS =                                       'num_dup_groups'
LOG_NUM_READ_GROUPS_WITH_UMI_ERROR =       'num_read_groups_with_umi_error'
LOG_NUM_READ_GROUPS_WITH_UMI_ERROR_DIST = (
                                      'num_read_groups_with_umi_error_dist')
LOG_NUM_READ_GROUPS_REJECTED_DUE_TO_UMI_ERROR_DIST = (
                           'num_read_groups_rejected_due_to_umi_error_dist')
# ReportDB
REPORT_DB_COUNT_METRICS = [
    LOG_NUM_LOCATIONS,
    LOG_NUM_UNIQUE_UMI_AND_LOCATION_COMBINATIONS,
    LOG_NUM_READ_GROUPS,
    LOG_NUM_DUP_GROUPS,
    LOG_NUM_READ_GROUPS_WITH_UMI_ERROR, ]
REPORT_DB_8_UMI_DIST_COUNT_METRICS = [
    LOG_NUM_READ_GROUPS_WITH_UMI_ERROR_DIST,
    LOG_NUM_READ_GROUPS_REJECTED_DUE_TO_UMI_ERROR_DIST, ]


# Pad the read_group_id with zeros until you have this many digits.
READ_GROUP_ID_DIGITS =                                                   10
## Delimiters for the read name annotations ##
# Delimiter to separate read names from their annotations
DELIM_ANNO = '-'
# Delimiter to separate read pairs
DELIM_ANNO_READ_PAIR = '^'
# Delimiter to separate records of different types
DELIM_ANNO_TYPE = ';'
# Delimiter to seperate records of the same type
DELIM_ANNO_ELEMENT = ','

## Other delimiters
# Delimiter to separate SAM file fields
DELIM_SAM_FIELD = '\t'

# Delimiter to separate elements of a list in a SimpleBucketLmdb
# Note: chr(30) is ACSII "record separator"
DELIM_SAM_LIST_LMDB = chr(30)

# Default delimiter to separate items in a SimpleBucketDb
DELIM_BUCKET_LIST = ','

# Delimiter to separate a ReadGroup's metadata from the SAM records the
# ReadGroup contains.
# Note: chr(29) is ACSII "group separator"
DELIM_READ_GROUP_METADATA_SAM_RECORDS = chr(29)

## Database stuff
STORE_OPTION_LMDB = 'lmdb'
STORE_OPTION_MEMORY = 'memory'

### LMDB stuff ###
# 1TB database size
LMDB_DB_SIZE = 1024**4
LMDB_MAX_DBS = 10
RECORDS_PER_TXN = 1000000
RECORDS_PER_TXN = 100000
# RECORDS_PER_TXN = 1
# RECORDS_PER_TXN = 5000000
# RECORDS_PER_TXN = 31
# RECORDS_PER_TXN = 1
# RECORDS_PER_TXN = 3
# RECORDS_PER_TXN = 500

# File suffixes
# For FASTQ reads that are rejected (e.g. UMI quality score too low)
SUFFIX_REJECTS =                                                  'rejects'
# After --remove-umi is run.
SUFFIX_REMOVE_UMI =                                                 'rmumi'
# After remove-adapter is run.
SUFFIX_REMOVE_ADAPTER =                                           'rmadapt'
# For the "too-short" files produced by remove-adapter.
SUFFIX_REMOVE_ADAPTER_TOO_SHORT =                                'tooshort'
# After --qtrim is run.
SUFFIX_QTRIM =                                                      'qtrim'
SUFFIX_QTRIM_UNPAIRED =                                          'unpaired'
# After --annotate-qtrim umi is run.
SUFFIX_ANNOTATE_QTRIM =                                              'anno'

# A 'PCR or optical duplicate' is marked with 0x400 in the FLAG field of SAM
# files.
SAM_FORMAT_FLAG_DUPLICATE = 0x400

# Number of characters in the random string of
TMP_FILE_NAME_RANDOM_STR_SIZE =                                           6

# Default random seed
RANDOM_SEED =                                                'Little Ashes'


# Dupligänger log filename
LOG_FILENAME =                                           'dupliganger.log'
# Overall log level
LOG_LEVEL =                                                         'DEBUG'
# Log level for dupliganger.log
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

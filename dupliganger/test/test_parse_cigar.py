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

import pytest
from pytest import fixture
from dupliganger.sam import parse_cigar
from dupliganger.common import HardClippingNotSupportedException

class TestParseCigar(object):
    """Test parse_cigar()."""

    #############
    ### Tests ###
    #############

    def test_simple(self):
        assert parse_cigar(100, '+', '1M') == (100, 100, 100, 100)
        assert parse_cigar(100, '-', '1M') == (100, 100, 100, 100)
        assert parse_cigar(100, '+', '101M') == (100, 100, 200, 200)
        assert parse_cigar(100, '-', '101M') == (200, 200, 100, 100)

    def test_left_soft_clip(self):
        assert parse_cigar(100, '+', '1S1M') == (99, 100, 100, 100)
        assert parse_cigar(100, '-', '1S1M') == (100, 100, 100, 99)
        assert parse_cigar(100, '+', '1S101M') == (99, 100, 200, 200)
        assert parse_cigar(100, '-', '1S101M') == (200, 200, 100, 99)

        assert parse_cigar(100, '+', '10S1M') == (90, 100, 100, 100)
        assert parse_cigar(100, '-', '10S1M') == (100, 100, 100, 90)
        assert parse_cigar(100, '+', '10S101M') == (90, 100, 200, 200)
        assert parse_cigar(100, '-', '10S101M') == (200, 200, 100, 90)

    def test_right_soft_clip(self):
        assert parse_cigar(100, '+', '1M1S') == (100, 100, 100, 101)
        assert parse_cigar(100, '-', '1M1S') == (101, 100, 100, 100)
        assert parse_cigar(100, '+', '101M1S') == (100, 100, 200, 201)
        assert parse_cigar(100, '-', '101M1S') == (201, 200, 100, 100)

        assert parse_cigar(100, '+', '1M10S') == (100, 100, 100, 110)
        assert parse_cigar(100, '-', '1M10S') == (110, 100, 100, 100)
        assert parse_cigar(100, '+', '101M10S') == (100, 100, 200, 210)
        assert parse_cigar(100, '-', '101M10S') == (210, 200, 100, 100)

    def test_left_and_right_soft_clip(self):
        assert parse_cigar(100, '+', '1S1M1S') == (99, 100, 100, 101)
        assert parse_cigar(100, '-', '1S1M1S') == (101, 100, 100, 99)
        assert parse_cigar(100, '+', '1S101M1S') == (99, 100, 200, 201)
        assert parse_cigar(100, '-', '1S101M1S') == (201, 200, 100, 99)

        assert parse_cigar(100, '+', '10S1M10S') == (90, 100, 100, 110)
        assert parse_cigar(100, '-', '10S1M10S') == (110, 100, 100, 90)
        assert parse_cigar(100, '+', '10S101M10S') == (90, 100, 200, 210)
        assert parse_cigar(100, '-', '10S101M10S') == (210, 200, 100, 90)

    def test_sam_format_spec(self):
        # See 'Sequence Alignment/Map Format Specification', 2 Sep 2016.
        # Specifically, these are taken from the SAM file format specification,
        # section 1.1 ("An example").

        # +r001/1
        assert parse_cigar(7, '+', '8M2I4M1D3M') == (7, 7, 22, 22)
        # +r002
        assert parse_cigar(9, '+', '3S6M1P1I4M') == (6, 9, 18, 18)
        # +r003
        assert parse_cigar(9, '+', '5S6M') == (4, 9, 14, 14)
        # +r004
        assert parse_cigar(16, '+', '6M14N5M') == (16, 16, 40, 40)
        # -r003, hard clipping, we don't support it...
        with pytest.raises(HardClippingNotSupportedException,
                message='Dupligänger does not support hard-clipping. cigar: 6H5M, left pos: 29, strand: -'):
            parse_cigar(29, '-', '6H5M') == (16, 16, 40, 40)
        # -r001/2
        assert parse_cigar(37, '-', '9M') == (45, 45, 37, 37)

# vim: softtabstop=4:shiftwidth=4:expandtab

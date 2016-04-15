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

from pytest import fixture
from superdeduper.module1 import SomeClassToTest

def helper_func(args):
    """Helper function."""
    pass

class TestSomeClassToTest:
    """Test SomeClassToTest."""

    ################
    ### Fixtures ###
    ################

    @fixture
    def some_fixture_A(self):
        return None

    @fixture
    def some_fixture_B(self):
        return None

    #############
    ### Tests ###
    #############

    def test_something_1(self, some_fixture_A, some_fixture_B):
        c = SomeClassToTest(some_fixture_A, some_fixture_B)
        assert c.is_something
        assert not c.is_something_else
        assert c.some_method() == True

    def test_something_2(self, some_fixture_A, some_fixture_B):
        c = SomeClassToTest(some_fixture_A, some_fixture_B)
        assert c.is_something
        assert not c.is_something_else
        assert c.some_method() == True

# vim: softtabstop=4:shiftwidth=4:expandtab

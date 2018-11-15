#!/usr/bin/env python

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

# This file allows you to run superdeduper (for development purposes) like so:
#   git clone ...superdeduper
#   cd superdeduper
#   python -m superdeduper

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# SuperDeDuper imports
from superdeduper import superdeduper

def main():
    superdeduper.main()

if __name__ == "__main__":
    main()

# vim: softtabstop=4:shiftwidth=4:expandtab

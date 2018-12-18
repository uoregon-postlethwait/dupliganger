#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

# This file allows you to run dupliganger (for development purposes) like so:
#   git clone ...dupliganger
#   cd dupliganger
#   python -m dupliganger

# Python 3 imports
from __future__ import absolute_import
from __future__ import division

# Dupligänger imports
from dupliganger import dupliganger

def main():
    dupliganger.main()

if __name__ == "__main__":
    main()

# vim: softtabstop=4:shiftwidth=4:expandtab

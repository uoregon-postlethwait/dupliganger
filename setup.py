# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os import path
from codecs import open  # To use a consistent encoding
import sys

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# List of required packages for python 2 and 3.
install_requires=['docopt', 'lmdb', 'distance', 'future', 'psutil']

# List of backported required packages for python2.
if sys.version_info[0] == 2:
    install_requires += [
            # For lru_cache
            'functools32',
            # For unix-like "which" tool.
            'whichcraft']

setup(
    name='dupliganger',
    version='0.92',

    description="A reference-based, UMI-aware, 5ʹ-trimming-aware PCR duplicate removal pipeline.",
    long_description=long_description,

    # Dupligänger's homepage.
    url='https://github.com/uoregon-postlethwait/dupliganger',

    # Author details
    author='Postlethwait Lab, University of Oregon',
    author_email='postlethwait.lab@gmail.com',

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        # Who Dupligänger is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',

        # License
        'License :: Free for non-commercial use',

        # Python versions supported.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    keywords='bioinformatics',
    zip_safe=True,

    # Packages provided.
    packages=['dupliganger'],

    # Required packages.
    install_requires=install_requires,

    # Require Python 2.7 or any versions of Python 3 starting with 3.4:
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',

    # Reference the License
    license = 'LICENSE.txt',

    # The dupliganger command line tool.
    entry_points={
        'console_scripts': [
            'dupliganger=dupliganger.command_line:main_wrapper',
        ],
    },

    # URLs
    project_urls={
        'Source': 'https://github.com/uoregon-postlethwait/dupliganger',
        'Bug Reports': 'https://github.com/uoregon-postlethwait/dupliganger/issues',
    },
)

# vim: softtabstop=4:shiftwidth=4:expandtab

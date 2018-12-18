from os import path
here = path.abspath(path.dirname(__file__))
__version__ = None
with open(path.join(here, 'VERSION')) as f:
    __version__ = f.readline().strip()

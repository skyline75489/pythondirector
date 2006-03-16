import pdlogging
try:
    from pdnetworktwisted import *
except ImportError:
    pdlogging.log("no twisted available - falling back to asyncore")
    from pdnetworkasyncore import *

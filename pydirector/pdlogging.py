#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdlogging.py,v 1.3 2002/07/03 09:17:23 anthonybaxter Exp $
#

Logger=None

from asyncore import compact_traceback

import sys


# look at replacing this later
class _LoggerClass:
    def __init__(self, logfile=None):
        self.logfile = logfile
        self.fp = None
        self.reopen()

    def reopen(self):
        if self.logfile is not None and self.fp is not None:
            del self.fp
        if self.logfile is None:
            self.fp = sys.stderr
        else:
            self.fp = open(self.logfile, 'a')

    def log(self, message):
        self.fp.write(message)
        self.fp.flush()

def initlog(filename):
    global Logger
    Logger = _LoggerClass(filename)

def log(message):
    global Logger
    if Logger is None: Logger = _LoggerClass()
    Logger.log(message)

def reload():
    global Logger
    if Logger is None: Logger = _LoggerClass()
    Logger.reload()

#!/usr/bin/env python

# main driver script for pythondirector

#
# Copyright (c) 2002-2006 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pydir.py,v 1.13 2006/03/17 13:20:55 anthonybaxter Exp $
#

import sys, resource

def versionCheck():
    MINVERSION = (2,2)
    if not (hasattr(sys, 'version_info') and sys.version_info >= MINVERSION):
        raise RuntimeError("PythonDirector needs >= Python %d.%d"%MINVERSION)

def main():
    from pydirector.pdmain import PythonDirector
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
    config = sys.argv[1]
    pd = PythonDirector(config)
    pd.start(profile=0)

if __name__ == "__main__":
    versionCheck()
    main()


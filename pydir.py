#!/usr/bin/env python

# main driver script for pythondirector

import sys

def versionCheck():
    if not (hasattr(sys, 'version_info') and sys.version_info > (2,1)):
        raise RuntimeError, "PythonDirector needs Python2.1 or greater"

def main():
    from pydirector.pdmain import PythonDirector
    config = sys.argv[1]
    pd = PythonDirector(config)
    pd.start()

if __name__ == "__main__":
    versionCheck()
    main()

#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pydir.py,v 1.7 2002/11/26 06:32:40 anthonybaxter Exp $
#

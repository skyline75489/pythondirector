#!/usr/bin/env python

# main driver script for pythondirector

import sys, resource

def versionCheck():
    if not (hasattr(sys, 'version_info') and sys.version_info > (2,1)):
        raise RuntimeError, "PythonDirector needs Python2.1 or greater"

def main():
    from pydirector.pdmain import PythonDirector
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
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
# $Id: pydir.py,v 1.8 2003/04/30 06:07:30 anthonybaxter Exp $
#

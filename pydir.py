#!/usr/bin/env python

#   
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#   

import sys

def versionCheck():
    if not (hasattr(sys, 'version_info') and sys.version_info > (2,2)):
	raise RuntimeError, "PythonDirector needs Python2.2"

def main():
    from pydirector.pdmain import PythonDirector
    config = sys.argv[1]
    pd = PythonDirector(config)
    pd.start()

if __name__ == "__main__":
    versionCheck()
    main()

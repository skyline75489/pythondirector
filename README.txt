This is a pure-python TCP load balancer. It takes inbound TCP
connections and connects them to one of a number of backend
servers. 

Features:

  - async i/o based, so much less overhead than fork/thread based
    balancers

  - Multiple scheduling algorithms (random, round robin, leastconns)

  - If a server fails to answer, it's removed from the pool - the
    client that failed to connect gets transparently failed over to 
    a new host.

  - xml based configuration file

  - seperate management thread that periodically re-adds failed hosts
    if they've come back up.

  - optional builtin webserver for admin

API (web based):

Admin interface: 

  running / running.txt 
    current configuration and status of the PD (HTML / text)

  config.xml - 
    initial config of the PD (xml)

  running.xml
    current running config of the PD (xml)

  Host mgmt:
    addHost?service=NNN&group=NNN&ip=NNN:n -
        add a new host to the group of a service
    delHost?service=NNN&group=NNN&name=NNN:n -
        remove a host from the group of a service
    delAllHosts?service=NNN&group=NNN -
        remove all hosts from the group of a service

    Note that the last two will not let you remove all hosts
    from the enabled group.

  group mgmt:
    enableGroup?service=NNN&group=NNN -
        switch the currently enabled group. Note that this will
        not affect any in-progress connections.

    changeScheduler?service=NNN&group=NNN&scheduler=NNN

  user mgmt:
    ??

  service mgmt:
    ??

This software is covered by the following license:

Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/) 
and Anthony Baxter <anthony@interlink.com.au>

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.


#
# Copyright (c) 2002-2006 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdschedulers.py,v 1.18 2006/03/17 13:20:56 anthonybaxter Exp $
#


# XXX The current connection counting is crap. We need to keep some sort 
# of connection tokens that get mapped to the backend.

import sys
import pdconf, pdlogging
from time import time

def createScheduler(groupConfig):
    schedulerName = groupConfig.scheduler
    if schedulerName == "random":
        return RandomScheduler(groupConfig)
    elif schedulerName == "leastconns":
        return LeastConnsScheduler(groupConfig)
    elif schedulerName == "roundrobin":
        return RoundRobinScheduler(groupConfig)
    elif schedulerName == "leastconnsrr":
        return LeastConnsRRScheduler(groupConfig)
    else:
        raise ValueError("Unknown scheduler type `%s'"%schedulerName)

class BaseScheduler:

    schedulerName = "base"

    def __init__(self, groupConfig):
        self.hosts = []
        self.hostnames = {}
        self.badhosts = {}
        self.open = {}
        self.openconns = {}
        self.totalconns = {}
        self.lastclose = {}
        self.loadConfig(groupConfig)

    def loadConfig(self, groupConfig):
        self.group = groupConfig
        hosts = self.group.getHosts()
        for host in hosts:
            self.newHost(host.ip, host.name)
        #print self.hosts

    def getStats(self, verbose=0):
        """ Returns a dict containing three items - open, totals, bad
            open and totals are dicts of host:port to counts
            bad is a dict of host:port to (time,reason)
        """
        out = {}
        out['open'] = {}
        out['totals'] = {}
        hc = self.openconns.items() # (host,port), count
        hc.sort()
        for h,c in hc:
            out['open']['%s:%s'%h] = c
        hc = self.totalconns.items()
        hc.sort()
        for h,c in hc:
            out['totals']['%s:%s'%h] = c
        bh = self.badhosts
        out['bad'] = bh
        return out

    def showStats(self, verbose=1):
        out = []
        out.append( "%d open connections"%len(self.open.keys()) )
        hc = self.openconns.items()
        hc.sort()
        out = out + [str(x) for x in hc]
        if verbose:
            oh = [x[1] for x in self.open.values()]
            oh.sort()
            out = out + [str(x) for x in oh]
        return "\n".join(out)

    def getHost(self, s_id, client_addr=None):
        host = self.nextHost(client_addr)
        if host:
            cur = self.openconns.get(host)
            self.open[s_id] = (time(),host)
            self.openconns[host] = cur+1
            return host
        else:
            return None

    def getHostNames(self):
        return self.hostnames

    def doneHost(self, s_id):
        try:
            t,host = self.open[s_id]
        except KeyError:
            #print "Couldn't find %s in %s"%(repr(s_id), repr(self.open.keys()))
            return
        del self.open[s_id]
        cur = self.openconns.get(host)
        if cur is not None:
            self.openconns[host] = cur - 1
            self.totalconns[host] += 1
        self.lastclose[host] = time()

    def newHost(self, ip, name):
        if type(ip) is not type(()):
            ip = pdconf.splitHostPort(ip)
        self.hosts.append(ip)
        self.hostnames[ip] = name
        self.hostnames['%s:%d'%ip] = name
        self.openconns[ip] = 0
        self.totalconns[ip] = 0

    def delHost(self, ip=None, name=None, activegroup=0):
        "remove a host"
        if ip is not None:
            if type(ip) is not type(()):
                ip = pdconf.splitHostPort(ip)
        elif name is not None:
            for ip in self.hostnames.keys():
                if self.hostnames[ip] == name:
                    break
            raise ValueError("No host named %s"%(name))
        else:
            raise ValueError("Neither ip nor name supplied")
        if activegroup and len(self.hosts) == 1:
            return 0
        if ip in self.hosts:
            self.hosts.remove(ip)
            del self.hostnames[ip]
            del self.openconns[ip]
            del self.totalconns[ip]
        elif ip in self.badhosts:
            del self.badhosts[ip]
        else:
            raise ValueError("Couldn't find host")
        return 1

    def deadHost(self, s_id, reason=''):
        t,host = self.open[s_id]
        if host in self.hosts:
            pdlogging.log("marking host %s down (%s)\n"%(str(host), reason),
                            datestamp=1)
            self.hosts.remove(host)
        if host in self.openconns:
            del self.openconns[host]
        if host in self.totalconns:
            del self.totalconns[host]
        self.badhosts[host] = (time(), reason)
        # make sure we also mark this session as done.
        self.doneHost(s_id)

    def nextHost(self, client_addr):
        "Override this in a subclass to actually do the work!"
        raise NotImplementedError

class RandomScheduler(BaseScheduler):
    schedulerName = "random"

    def nextHost(self, client_addr):
        import random
        if self.hosts:
            pick = random.choice(self.hosts)
            return pick
        else:
            return None

class RoundRobinScheduler(BaseScheduler):
    schedulerName = "roundrobin"
    counter = 0

    def nextHost(self, client_addr):
        if not self.hosts:
            return None
        if self.counter >= len(self.hosts):
            self.counter = 0
        if self.hosts:
            d = self.hosts[self.counter]
            self.counter += 1
            return d
        else:
            return None

class LeastConnsScheduler(BaseScheduler):
    """
        This scheduler passes the connection to the destination with the
        least number of current open connections. This is a very cheap
        and quite accurate method of load balancing. But see the 
        LeastConnsRRScheduler for a slightly better version.
    """
    schedulerName = "leastconns"
    counter = 0

    def nextHost(self, client_addr):
        if not self.openconns.keys():
            return None
        hosts = [ (x[1],x[0]) for x in self.openconns.items() ]
        hosts.sort()
        return hosts[0][1]

class LeastConnsRRScheduler(BaseScheduler):
    """
        The basic LeastConnsScheduler has a problem - it sorts by
        open connections, then by hostname. So hostnames that are
        earlier in the alphabet get many many more hits. This is
        suboptimal. This one round-robins by the "lastclose" mapping
        to distribute the load more equitably.
    """
    schedulerName = "leastconnsrr"
    counter = 0

    def nextHost(self, client_addr):
        if not self.openconns.keys():
            return None
        hosts = [ (x[1], self.lastclose.get(x[0],0), x[0]) 
                            for x in self.openconns.items() ]
        hosts.sort()
        return hosts[0][2]


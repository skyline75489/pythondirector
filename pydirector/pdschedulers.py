#   
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#   
# $Id: pdschedulers.py,v 1.2 2002/07/01 05:33:16 anthonybaxter Exp $
#

import sys
if sys.version_info < (2,2):
    class object: pass

import pdconf

def createScheduler(groupConfig):
    schedulerName = groupConfig.scheduler
    if schedulerName == "random":
        return RandomScheduler(groupConfig)
    elif schedulerName == "leastconns":
        return LeastConnsScheduler(groupConfig)
    elif schedulerName == "roundrobin":
        return RoundRobinScheduler(groupConfig)
    else:
        raise ValueError, "Unknown scheduler type `%s'"%schedulerName

class BaseScheduler:

    schedulerName = "base"

    def __init__(self, groupConfig):
        self.hosts = []
        self.hostnames = {}
        self.badhosts = {}
        self.open = {}
        self.openconns = {}
        self.loadConfig(groupConfig)

    def loadConfig(self, groupConfig):
        self.group = groupConfig
        hosts = self.group.getHosts()
        for host in hosts:
            self.newHost(host.ip, host.name)
        #print self.hosts

    def getStats(self, verbose=0):
        out = {}
        out['open'] = {}
        hc = self.openconns.items()
        hc.sort()
        for h,c in hc:
            out['open']['%s:%s'%h] = c
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

    def getHost(self, s_id):
        from time import time
        host = self.nextHost()
        if host:
            cur = self.openconns.get(host)
            self.open[s_id] = (time(),host)
            self.openconns[host] = cur+1
            return host

    def getHostNames(self):
        return self.hostnames

    def doneHost(self, s_id):
        t,host = self.open[s_id]
        del self.open[s_id]
        cur = self.openconns.get(host)
        if cur is not None:
            self.openconns[host] = cur - 1

    def newHost(self, ip, name):
        if type(ip) is not type(()):
            ip = pdconf.splitHostPort(ip)
        self.hosts.append(ip)
        self.hostnames[ip] = name
        self.hostnames['%s:%d'%ip] = name
        self.openconns[ip] = 0

    def delHost(self, ip=None, name=None):
        "remove a host"
        if ip is not None:
            if type(ip) is not type(()):
                ip = pdconf.splitHostPort(ip)
        elif name is not None:
            for ip in self.hostnames.keys():
                if self.hostnames[ip] == name:
                    break
            raise ValueError, "No host named %s"%(name)
        else:
            raise ValueError, "Neither ip nor name supplied"
        if ip in self.hosts:
            self.hosts.remove(ip)
            del self.hostnames[ip] 
            del self.openconns[ip] 
        elif self.badhosts.has_key(ip):
            del self.badhosts[ip]
        else:
            raise ValueError, "Couldn't find host"

    def deadHost(self, s_id, reason=''):
        from time import time
        t,host = self.open[s_id]
        if host in self.hosts:
            self.hosts.remove(host)
        if self.openconns.has_key(host):
            del self.openconns[host]
        self.badhosts[host] = (time(), reason)
        # make sure we also mark this session as done.
        self.doneHost(s_id)

    def nextHost(self):
        raise NotImplementedError

class RandomScheduler(BaseScheduler):
    schedulerName = "random"

    def nextHost(self):
        import random
        if self.hosts:
            pick = random.choice(self.hosts)
            return pick

class RoundRobinScheduler(BaseScheduler):
    schedulerName = "roundrobin"
    counter = 0

    def nextHost(self):
        if self.counter >= len(self.hosts):
            self.counter = 0
        if self.hosts:
            d = self.hosts[self.counter]
            self.counter += 1
            return d

class LeastConnsScheduler(BaseScheduler):
    """
        This scheduler passes the connection to the destination with the
        least number of current open connections. This is a very cheap
        and quite accurate method of load balancing.
    """
    schedulerName = "leastconns"
    counter = 0

    def nextHost(self):
        hosts = [ (x[1],x[0]) for x in self.openconns.items() ]
        hosts.sort()
        return hosts[0][1]
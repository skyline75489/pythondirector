#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdmanager.py,v 1.6 2002/11/26 03:53:50 anthonybaxter Exp $
#

import sys
if sys.version_info < (2,2):
    class object: pass

import pdconf, pdlogging


class SchedulerManager(object):
    """
        This object sits in a seperate thread and manages the scheduler.
        It's responsible for reconfiguration, checking dead hosts to see
        if they've come back, that sort of thing.
    """
    def __init__(self, director, sleeptime=30, checktime=120):
        self.director = director
        self.sleeptime = sleeptime
        self.checktime = checktime

    def mainloop(self):
        import time
        while 1:
            time.sleep(self.sleeptime)
            for listeners in self.director.listeners.values():
                # since all listeners for a service share a scheduler,
                # we only need to check the first listener.
                listener = listeners[0]
                scheduler = listener.scheduler
                #print scheduler.showStats(verbose=0)
                self.checkBadHosts(scheduler)

    def checkBadHosts(self, scheduler):
        import time
        badhosts = scheduler.badhosts
        hosts = badhosts.keys()
        for bh in hosts:
            now = time.time()
            when,what = badhosts[bh]
            if now > when + self.checktime:
                pdlogging.log("re-adding %s automatically\n"%str(bh),
                        datestamp=1)
                name = scheduler.getHostNames()[bh]
                del badhosts[bh]
                scheduler.newHost(bh, name)

#   
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#   

import pdconf


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
            for listener in self.director.listeners.values():
                scheduler = listener.scheduler
                print scheduler.showStats(verbose=0)
                self.checkBadHosts(scheduler)

    def checkBadHosts(self, scheduler):
        import time
        badhosts = scheduler.badhosts
        hosts = badhosts.keys()
        for bh in hosts:
            now = time.time()
            when,what = badhosts[bh]
            if now > when + self.checktime:
                print "time to re-check", bh
                del badhosts[bh]
                scheduler.newHost(bh)

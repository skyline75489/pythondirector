#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdmain.py,v 1.3 2002/07/03 09:17:23 anthonybaxter Exp $
#

import sys
if sys.version_info < (2,2):
    class object: pass

class PythonDirector(object):

    def __init__(self, config):
        from pydirector import pdconf
        self.listeners = {}
        self.schedulers = {}
        self.manager = None
        self.conf = pdconf.PDConfig(config)
        self.createManager()
        self.createListeners()

    def start(self):
        import asyncore, sys
        from pydirector import pdadmin
        if self.conf.admin is not None:
            pdadmin.start(adminconf=self.conf.admin, director=self)
        self.manager.start()
        try:
            asyncore.loop(timeout = 4)
        except KeyboardInterrupt:
            sys.exit(0)

    def createManager(self):
        from pydirector import pdmanager
        import threading
        manager = pdmanager.SchedulerManager(self, sleeptime=30)
        mt = threading.Thread(target=manager.mainloop)
        mt.setDaemon(1)
        self.manager = mt

    def createSchedulers(self, service):
        from pydirector import pdschedulers
        for group in service.getGroups():
            s = pdschedulers.createScheduler(group)
            self.schedulers[(service.name,group.name)] = s

    def getScheduler(self, serviceName, groupName):
        return self.schedulers[(serviceName,groupName)]

    def createListeners(self):
        from pydirector import pdnetwork, pdconf
        for service in self.conf.getServices():
            self.createSchedulers(service)
            eg = service.getEnabledGroup()
            scheduler = self.getScheduler(service.name, eg.name)
            l = pdnetwork.Listener(service.name,
                                   pdconf.splitHostPort(service.listen),
                                   scheduler)
            self.listeners[service.name] = l

    def enableGroup(self, serviceName, groupName):
        serviceConf = self.conf.getService(serviceName)
        group = serviceConf.getGroup(groupName)
        if group:
            serviceConf.enabledgroup = groupName
        self.switchScheduler(serviceName)

    def switchScheduler(self, serviceName):
        """
            switch the scheduler for a listener. this is needed, e.g. if
            we change the active group
        """
        serviceConf = self.conf.getService(serviceName)
        eg = serviceConf.getEnabledGroup()
        scheduler = self.getScheduler(serviceName, eg.name)
        self.listeners[serviceName].scheduler = scheduler

#
# Copyright (c) 2002-2006 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdconf.py,v 1.24 2006/07/27 06:58:27 anthonybaxter Exp $
#

def getDefaultArgs(methodObj):
    import inspect
    arglist, vaarg, kwarg, defargs = inspect.getargspec(methodObj.im_func)
    arglist.reverse()
    defargs = list(defargs)
    defargs.reverse()
    ad = {}
    for a,v in zip(arglist, defargs):
        ad[a] = v
    return ad

def splitHostPort(s):
    h,p = s.split(':')
    p = int(p)
    if h == '*':
        h = ''
    return h,p

class ConfigError(Exception): pass
class ServiceError(ConfigError): pass
class GroupError(ServiceError): pass

class PDHost(object):
    __slots__ = [ 'name', 'ip' ]

    def __init__(self, name, ip):
        self.name = name
        if type(ip) is type(u''):
            self.ip = ip.encode('ascii')
        else:
            self.ip = ip

class PDGroup(object):
    __slots__ = [ 'name', 'scheduler', 'hosts' ]

    def __init__(self, name):
        self.name = name
        self.scheduler = None
        self.hosts = {}

    def getHost(self,name):
        return self.hosts[name]

    def getHostNamess(self):
        return self.hosts.keys()

    def getHosts(self):
        return self.hosts.values()

    def addHost(self, name, ip):
        self.hosts[name] = PDHost(name, ip)

    def delHost(self, name):
        del self.hosts[name]

class PDService(object):
    __slots__ = [ 'listen', 'groups', 'enabledgroup', 'name' ]
    def __init__(self, name):
        self.name = name
        self.groups = {}
        self.listen = []
        self.enabledgroup = None

    def loadGroup(self, groupobj):
        groupName = groupobj.getAttribute('name')
        newgroup = PDGroup(groupName)
        newgroup.scheduler = groupobj.getAttribute('scheduler')
        cc = 0
        for host in groupobj.childNodes:
            if host.nodeName in ("#text", "#comment"): continue
            if host.nodeName != u'host':
                raise ConfigError("expected 'host', got '%s'"%host.nodeName)
            name = host.getAttribute('name')
            if not name: name = 'host.%s'%cc
            newgroup.addHost(name, host.getAttribute('ip'))
            cc += 1
        self.groups[groupName] = newgroup

    def getGroup(self, groupName):
        return self.groups.get(groupName)

    def getGroups(self):
        return self.groups.values()

    def getGroupNames(self):
        return self.groups.keys()

    def getEnabledGroup(self):
        return self.groups.get(self.enabledgroup)

    def checkSanity(self):
        if not self.name:
            raise ServiceError("no name set")
        if not self.listen:
            raise ServiceError("no listen address set")
        if not self.groups:
            raise ServiceError("no host groups")
        if not self.enabledgroup:
            raise ServiceError("no group enabled")
        if not self.groups.get(self.enabledgroup):
            raise GroupError("enabled group '%s' not defined"%self.enabledgroup)
        for group in self.groups.values():
            if not group.name:
                raise GroupError("no group name set")
            if not group.scheduler:
                raise GroupError("no scheduler set for %s"%group.name)
            if not group.hosts:
                raise GroupError("no hosts set for %s"%group.name)

class PDAdminUser(object):
    __slots__ = [ 'name', 'password', 'access' ]

    def checkPW(self, password):
        from crypt import crypt
        if crypt(password, self.password[:2]) == self.password:
            return 1
        else:
            return 0

    def checkAccess(self, methodObj, argdict):
        a = getDefaultArgs(methodObj)
        required = a.get('Access', 'NoAccess')
        if required == "Read" and self.access in ('full', 'readonly'):
            return 1
        elif required == "Write" and self.access == 'full':
            return 1
        else:
            return 0


class PDAdmin(object):
    __slots__ = [ 'listen', 'userdb', 'secure' ]
    def __init__(self):
        self.listen = None
        self.secure = None
        self.userdb = {}

    def addUser(self, name, password, access):
        u = PDAdminUser()
        u.name = name
        u.password = password
        u.access = access
        self.userdb[name] = u

    def delUser(self, name):
        if name in self.userdb:
            del self.userdb[name]
            return 1
        else:
            return 0

    def loadUser(self, userobj):
        name = userobj.getAttribute('name')
        password = userobj.getAttribute('password')
        access = userobj.getAttribute('access')
        self.addUser(name, password, access)

    def getUser(self, name):
        return self.userdb.get(name)

    def getUsers(self):
        return self.userdb.values()

    def getUserNames(self):
        return self.userdb.keys()


class PDConfig(object):
    __slots__ = [ 'services', 'admin', 'dom', 'logging_file', 'checktime' ]

    def __init__(self, filename=None, xml=None):
        import pdlogging
        self.services = {}
        self.admin = None
        self.logging_file = None
        self.checktime = None
        dom = self._loadDOM(filename, xml)
        if dom.nodeName != 'pdconfig':
            raise ConfigError("expected top level 'pdconfig', got '%s'"%(
                                                                dom.nodeName))
        for item in dom.childNodes:
            if item.nodeName in ("#text", "#comment"):
                continue
            if item.nodeName not in ('service','admin','logging','checktime'):
                raise ConfigError(
                    "expected one of 'service','admin','logging','checktime'"
                    ", got '%s'"%item.nodeName)
            if item.nodeName == u'service':
                self.loadService(item)
            elif item.nodeName == u'admin':
                if self.admin is None:
                    self.loadAdmin(item)
                else:
                    raise ConfigError("only one 'admin' block allowed")
            elif item.nodeName == u'logging':
                self.logging_file = item.getAttribute('file')
                pdlogging.initlog(item.getAttribute('file'))
            elif item.nodeName == u'checktime':
                self.checktime = int(item.getAttribute('time'))

    def _loadDOM(self, filename, xml):
        from xml.dom.minidom import parseString
        if filename is not None:
            xml = open(filename).read()
        elif xml is None:
            raise ConfigError("need filename or xml")
        self.dom = parseString(xml)
        return self.dom.childNodes[0]

    def loadAdmin(self, admin):
        adminServer = PDAdmin()
        adminServer.listen = splitHostPort(admin.getAttribute('listen'))
        if admin.hasAttribute('secure'):
            adminServer.secure = admin.getAttribute('secure')
        for user in admin.childNodes:
            if user.nodeName in ("#text", "#comment"): continue
            if user.nodeName == u'user':
                adminServer.loadUser(user)
            else:
                raise ConfigError("only expect to see users in admin block")
        self.admin = adminServer

    def getService(self, serviceName):
        return self.services.get(serviceName)

    def getServices(self):
        return self.services.values()

    def getServiceNames(self):
        return self.services.keys()

    def loadService(self, service):
        serviceName = service.getAttribute('name')
        newService = PDService(serviceName)
        for c in service.childNodes:
            if c.nodeName in ("#text", "#comment"): continue
            if c.nodeName == u'listen':
                newService.listen.append(c.getAttribute('ip'))
            elif c.nodeName == u'group':
                newService.loadGroup(c)
            elif c.nodeName == u'enable':
                newService.enabledgroup = c.getAttribute('group')
            elif c.nodeName == "#comment":
                continue
            else:
                raise ConfigError("unknown node '%s'"%c.nodeName)
        newService.checkSanity()
        self.services[serviceName] = newService

    def setLoggingFile(self, filename):
        self.logging_file = filename
        #import pdlogging
        #pdlogging.initlog(self.logging_file)

    def toxml(self, director, verbose=0):
        from xml.dom.minidom import Document
        doc = Document()
        top = doc.createElement("pdconfig")
        doc.appendChild(top)

        # first, services
        for service in self.getServices():
            top.appendChild(doc.createTextNode("\n    "))
            serv = doc.createElement("service")
            serv.setAttribute('name', service.name)
            top.appendChild(serv)
            for l in service.listen:
                serv.appendChild(doc.createTextNode("\n        "))
                lobj = doc.createElement("listen")
                lobj.setAttribute('ip', l)
                serv.appendChild(lobj)
            groups = service.getGroups()
            for group in groups:
                serv.appendChild(doc.createTextNode("\n        "))
                sch = director.getScheduler(service.name, group.name)
                xg = doc.createElement("group")
                xg.setAttribute('name', group.name)
                xg.setAttribute('scheduler', sch.schedulerName)
                serv.appendChild(xg)
                stats = sch.getStats(verbose=verbose)
                #hosts = group.getHosts()
                hdict = sch.getHostNames()
                counts = stats['open']
                ahosts = counts.keys() # ahosts is now a list of active hosts
                # now add disabled hosts.
                for k in stats['bad'].keys():
                    ahosts.append('%s:%s'%k)
                ahosts.sort()
                for h in ahosts:
                    xg.appendChild(doc.createTextNode("\n            "))
                    xh = doc.createElement("host")
                    xh.setAttribute('name', hdict[h])
                    xh.setAttribute('ip', h)
                    xg.appendChild(xh)
                xg.appendChild(doc.createTextNode("\n        "))
            serv.appendChild(doc.createTextNode("\n        "))
            eg = service.getEnabledGroup()
            xeg = doc.createElement("enable")
            xeg.setAttribute("group", eg.name)
            serv.appendChild(xeg)
            serv.appendChild(doc.createTextNode("\n    "))
        top.appendChild(doc.createTextNode("\n    "))

        # now the admin block
        admin = self.admin
        if admin is not None:
            xa = doc.createElement("admin")
            xa.setAttribute("listen", "%s:%s"%admin.listen)
            top.appendChild(xa)
            for user in admin.getUsers():
                xa.appendChild(doc.createTextNode("\n        "))
                xu = doc.createElement("user")
                xu.setAttribute("name", user.name)
                xu.setAttribute("password", user.password)
                xu.setAttribute("access", user.access)
                xa.appendChild(xu)
            xa.appendChild(doc.createTextNode("\n    "))
            top.appendChild(doc.createTextNode("\n    "))

        if self.logging_file is not None:
            xl = doc.createElement("logging")
            xl.setAttribute("file", self.logging_file)
            top.appendChild(xl)

        if self.checktime is not None:
            xl = doc.createElement("checktime")
            xl.setAttribute("time", str(self.checktime))
            top.appendChild(xl)

        # final newline
        top.appendChild(doc.createTextNode("\n"))

        # and spit out the XML
        return doc.toxml()

if __name__ == "__main__":
    import sys
    PDConfig(sys.argv[1])

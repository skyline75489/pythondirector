#   
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#   


def splitHostPort(s):
    h,p = s.split(':')
    p = int(p)
    return h,p

class ConfigError(Exception): pass
class ServiceError(ConfigError): pass
class GroupError(ServiceError): pass

class PDHost(object):
    __slots__ = [ 'name', 'ip' ]

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip

class PDGroup(object):
    __slots__ = [ 'name', 'scheduler', 'hosts' ]

    def __init__(self, name):
        self.name = name
        self.scheduler = None
        self.hosts = {}

    def getHost(self,name):
        return self.hosts[name]

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
        self.listen = None
        self.enabledgroup = None

    def loadGroup(self, groupobj):
        groupName = groupobj.getAttribute('name')
        newgroup = PDGroup(groupName)
        newgroup.scheduler = groupobj.getAttribute('scheduler')
        cc = 0
        for client in groupobj.childNodes:
            if client.nodeName == "#text": continue
            if client.nodeName != u'client':
                raise ConfigError, \
                    "expected 'client', got '%s'"%client.nodeName
            name = client.getAttribute('name')
            if not name: name = 'client.%s'%cc
            newgroup.addHost(name, client.getAttribute('ip'))
            cc += 1
        self.groups[groupName] = newgroup

    def getGroup(self, groupName):
        return self.groups.get(groupName)

    def getEnabledGroup(self):
        return self.groups.get(self.enabledgroup)

    def getGroups(self):
        return self.groups.values()

    def checkSanity(self):
        if not self.name: raise ServiceError, "no name set"
        if not self.listen: raise ServiceError, "no listen address set"
        if not self.groups: raise ServiceError, "no client groups"
        if not self.enabledgroup: raise ServiceError, "no group enabled"
        if not self.groups.get(self.enabledgroup): raise GroupError, \
                    "enabled group '%s' not defined"%self.enabledgroup
        for group in self.groups.values():
            if not group.name: raise GroupError, "no group name set"
            if not group.scheduler: raise GroupError, \
                    "no scheduler set for %s"%group.name
            if not group.hosts: raise GroupError, \
                    "no clients set for %s"%group.name

class PDAdminUser(object):
    __slots__ = [ 'name', 'password', 'access' ]

    def checkPW(self, password):
        from crypt import crypt
        if crypt(password, self.password[:2]) == self.password:
            return 1
        else:
            return 0


class PDAdmin(object):
    __slots__ = [ 'listen', 'userdb' ]
    def __init__(self):
        self.listen = None
        self.userdb = {}

    def addUserFromDOM(self, user):
        name = user.getAttribute('name')
        password = user.getAttribute('password')
        access = user.getAttribute('access')
        self.addUser(name, password, access)

    def addUser(self, name, password, access):
        u = PDAdminUser()
        u.name = name
        u.password = password
        u.access = access
        self.userdb[name] = u

    def getUser(self, name):
        return self.userdb.get(name)

class PDConfig(object):
    __slots__ = [ 'services', 'admin', 'dom' ]

    def __init__(self, filename):
        self.services = {}
        self.admin = None
        dom = self._loadDOM(open(filename))
        if dom.nodeName != 'pdconfig':
            raise ConfigError, "expected top level 'pdconfig'"
        for item in dom.childNodes:
            if item.nodeName == "#text": continue
            if item.nodeName not in ( u'service', u'admin' ):
                raise ConfigError, \
                    "expected 'service' or 'admin', got '%s'"%item.nodeName
            if item.nodeName == u'service':
                self.loadService(item)
            if item.nodeName == u'admin':
                if self.admin is None:
                    self.loadAdmin(item)
                else:
                    raise ConfigError, "only one 'admin' block allowed"

    def _loadDOM(self, file):
        from xml.dom.minidom import parseString
        self.dom = parseString(file.read())
        return self.dom.childNodes[0]

    def loadAdmin(self, admin):
        adminServer = PDAdmin()
        adminServer.listen = splitHostPort(admin.getAttribute('listen'))
        for user in admin.childNodes:
            if user.nodeName == "#text": continue
            if user.nodeName == u'user':
                adminServer.addUserFromDOM(user)
            else:
                raise ConfigError, "only expect to see users in admin block"
        self.admin = adminServer

    def getService(self, serviceName):
        return self.services.get(serviceName)

    def getServices(self):
        return self.services.values()

    def loadService(self, service):
        serviceName = service.getAttribute('name')
        newService = PDService(serviceName)
        for c in service.childNodes:
            if c.nodeName == "#text": continue
            if c.nodeName == u'listen':
                newService.listen = c.getAttribute('ip')
            elif c.nodeName == u'group':
                newService.loadGroup(c)
            elif c.nodeName == u'enable':
                newService.enabledgroup = c.getAttribute('group')
            else:
                raise ConfigError, "unknown node '%s'"%c.nodeName
        newService.checkSanity()
        self.services[serviceName] = newService

if __name__ == "__main__":
    import sys
    PDConfig(sys.argv[1])

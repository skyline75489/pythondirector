#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com) 
# and Anthony Baxter <anthony@interlink.com.au>
#
import threading, BaseHTTPServer, SocketServer, urlparse, re
import socket, time

def start(adminconf, director):
    AdminClass.director = director
    AdminClass.config = adminconf
    AdminClass.starttime = time.time()
    SocketServer.ThreadingTCPServer.allow_reuse_address = 1
    tcps = SocketServer.ThreadingTCPServer(adminconf.listen, AdminClass)
    at = threading.Thread(target=tcps.serve_forever)
    at.setDaemon(1)
    at.start()

class AdminClass(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = "Pydir/0.01"
    director = None
    config = None
    starttime = None

    def checkAuth(self, authstr):
        from base64 import decodestring
        type,auth = authstr.split()
        if type.lower() != 'basic':
            return None
        auth = decodestring(auth)
        user,pw = auth.split(':',1)
        userObj = self.config.getUser(user)
        if not ( userObj and userObj.checkPW(pw) ):
            # unknown user or incorrect pw
            return None
        else:
            return userObj.access.lower()

    def checkAccess(self, access, required):
        if required == "Read" and access in ('full', 'readonly'):
            return 1
        elif required == "Write" and access == 'full':
            return 1
        else:
            self.unauth(why='access privs')
            return 0


    def unauth(self, why):
        print "auth failure", why
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'basic realm="python director"')
        self.wfile.write("<p>Unauthorised</p>\n")

    def header(self, html=1):
        self.send_response(200)
        if html:
            self.send_header("Content-type", "text/html")
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        if html:
            W = self.wfile.write
            W("""<html><head><title>python director</title>
                 <link rel=stylesheet type="text/css" href="/pydirector.css">
                 </head></body>""")
            W("""
            <p class="title">Python Director version %s, running on host %s.</p>
            """%(self.server_version, socket.gethostname()))

    def footer(self, args):
        import urllib
        W = self.wfile.write
        W("""
            <p class="footer">
            [<a href="running">running</a> <a href="running.txt">(text)</a>]
            [<a href="config.xml">config.xml</a>] 
            [<a href="http://pythondirector.sf.net">pythondirector</a>] 
            </p>""")

        m = args.get('resultMessage')
        if m:
            m = urllib.unquote(m)
            W("""<p class="message">%s</p>"""%m)
        W("""</body></html>\n\n""")

    def redir(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()
        
    def do_GET(self):
        #print "URL",self.path
        h,p,u,p,q,f = urlparse.urlparse(self.path)

        authstr = self.headers.get('Authorization','')
        #print "authstr", authstr
        if authstr:
            access = self.checkAuth(authstr)
        if not (authstr and access):
            self.unauth(why='no valid auth')
            return

        if u == "/":
            self.pdadmin_index_html(dictify(q), access)
            return

        if u.startswith("/"):
            u = re.sub(r'\.', '_', u[1:])
        if hasattr(self, 'pdadmin_%s'%u):
            getattr(self, 'pdadmin_%s'%u)(dictify(q), access)
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><body>no such URL</body></html>")

    def pdadmin_pydirector_css(self, args, access):
        if not self.checkAccess(access, 'Read'): return
        self.header(html=0)
        self.wfile.write(PYDIR_CSS)

    def pdadmin_index_html(self, args, access):
        if not self.checkAccess(access, 'Read'): return
        self.header(html=1)
        self.wfile.write("""
            <p>Python Director version %s, running on %s</p>
            <p>Running since %s</p>
            """%(self.server_version,
                 socket.gethostname(),
                 time.ctime(self.starttime)))
        self.footer(args)

    def pdadmin_running_txt(self, args, access):
        if not self.checkAccess(access, 'Read'): return
        self.header(html=0)
        W = self.wfile.write
        conf = self.director.conf
        for service in conf.getServices():
            eg = service.getEnabledGroup()
            W('service %s %s %s\n'%(service.name, service.listen, eg.name))
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=args.get('verbose'))
                hosts = group.getHosts()
                hdict = {}
                for h in hosts:
                    hdict[h.ip] = h.name
                if group is eg:
                    klass = 'enabled'
                else:
                    klass = 'inactive'
                W('group %s %s\n'%(group.name, klass))
                counts = stats['open']
                k = counts.keys()
                k.sort() # k is now a list of hosts in the opencount stats 
                for h in k:
                    W("host %s %s "%(hdict[h], h))
                    if counts.has_key(h):
                        W("%s -\n"%counts[h])
                    else:
                        W("- -\n")
                bad = stats['bad']
                for k in bad:
                    host = '%s:%s'%k
                    W("disabled %s %s"%(hdict[host], host)) 
                    when,what = bad[k]
                    W(" %s -\n"%what)

    def pdadmin_running(self, args, access):
        if not self.checkAccess(access, 'Read'): return
        self.header(html=1)
        W = self.wfile.write
        W("<p><b>current config</b></p>\n")
        conf = self.director.conf
        for service in conf.getServices():
            W('<table><tr><th align="left" colspan="4">Service: %s</th></tr>\n'%
                                                        service.name)
            W('<tr><td colspan="4">Listening on %s</td></tr>\n'%service.listen)
            eg = service.getEnabledGroup()
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=args.get('verbose'))
                hosts = group.getHosts()
                hdict = {}
                for h in hosts:
                    hdict[h.ip] = h.name
                if group is eg:
                    klass = 'enabled'
                else:
                    klass = 'inactive'
                W('<tr class="%s"><td colspan="4">%s '%(klass, group.name))
                if group is eg:
                    W('<b>ENABLED</b>\n')
                else:
                    W('<a href="enableGroup?service=%s&group=%s">enable</a>\n'%
                                            (service.name, group.name))
                W('</td></tr>\n')
                W('''<tr class="%s"><th colspan="2">hosts</th>
                     <th>open</th><th>total</th></tr>\n'''%klass)
                counts = stats['open']
                k = counts.keys()
                k.sort()
                for h in k:
                    W('<tr class="%s"><td>'%klass)
                    W("%s</td><td><tt>%s</tt></td>\n"%(hdict[h], h))
                    if counts.has_key(h):
                        W("<td>%s</td><td>--</td>"%counts[h])
                    else:
                        W("<td>missing</td><td>--</td>")
                    W('</tr>')
                bad = stats['bad']
                if bad:
                    W('''<tr class="%s"><th colspan="2">disabled hosts</th>
                         <th>why</th><th>when</th></tr>\n'''%klass)
                for k in bad:
                    host = '%s:%s'%k
                    W('<tr class="%s"><td>'%klass)
                    W("%s</td><td><tt>%s</tt></td>\n"%(hdict[host], host)) # XXXX
                    when,what = bad[k]
                    W("<td>%s</td><td>--</td>"%what)
                    W('</tr>')
            W("</table>")
            W('<div class="adminForm">\n')
            #  add
            W('</div>\n')
        self.footer(args)

    def pdadmin_addHost(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.header(html=1)

    def pdadmin_delHost(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.header(html=1)

    def pdadmin_delAllHosts(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.header(html=1)

    def pdadmin_enableGroup(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.director.enableGroup(args['service'], args['group'])
        self.redir('/running?resultMessage=Group%%20%s%%20enabled%%20for%%20service%%20%s'%(
                args['group'], args['service']))
        self.wfile.write("OK\n")

    def pdadmin_changeScheduler(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.header(html=1)
        

    def pdadmin_config_xml(self, args, access):
        if not self.checkAccess(access, 'Write'): return
        self.header(html=0)
        self.wfile.write(self.director.conf.dom.toxml())

    def pdadmin_status_txt(self, args, access):
        if not self.checkAccess(access, 'Read'): return
        else: self.header(html=0)
        W = self.wfile.write
        verbose = args.get('verbose',0)
        for listener in self.director.listeners.values():
            sch_stats = listener.scheduler.getStats(verbose='verbose')
            lh,lp = listener.listening_address
            sn = listener.scheduler.schedulerName
            W("service: %s\n"%listener.name)
            W("listen: %s:%s %s\n"%(lh,lp, sn))
            for h, c in sch_stats['open']:
                W("host: %s:%s %s\n"%(h[0],h[1],c))
            bad = sch_stats['bad']
            if bad:
                for b in bad:
                    W("disabled: %s:%s\n"%b)

def dictify(q):
    """
    takes string of form '?a=b&c=d&e=f'
    and returns {'a':'b', 'c':'d', 'e':'f'}
    """
    from urllib import unquote
    out = {}
    if not q: return {}
    avs = q.split('&')
    for av in avs:
        print "av", av
        a,v = av.split('=',1)
        out[unquote(a)] = unquote(v)
    return out

def html_quote(str):
    return re.subn("<", "&lt;", str)[0]

PYDIR_CSS = """
A:link {color: #000000 }
A:visited {color: #000000}
p {
    font-family: helvetica; 
    font-size: 10pt 
}
p.footer {
    font-family: courier; 
    font-size: 8pt ;
    color: #000033 ; 
    background-color: #dddddd ; 
}
p.message {
    color: #000000 ; 
    background-color: #eeeeee ; 
    border: thin solid #ff0000 ;
    padding: 5px ;
}
p.bigbutton {
    color: #000000 ; 
    background-color: #eebbee ; 
    border: thin solid #cc4400 ;
    padding: 2px ;
}
p.button {
    color: #000000 ; 
    background-color: #eebbee ; 
    border: thin solid #cc4400 ;
    padding: 0px ;
}
p.title { 
    font-size: 10pt; 
    font-weight: bold; 
    color: #000033 ; 
    background-color: #dddddd ; 
}
td { 
    font-family: helvetica; 
    font-size: 10pt
}
tr.enabled { 
    background-color: #ccdddd; 
    color: #dd0000 
}
tr.inactive { 
    background-color: #eeeeee; 
    color: #000000 
}
th {
    font-family: helvetica ; 
    font-size: 10pt
}

"""

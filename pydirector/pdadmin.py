#
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com) 
# and Anthony Baxter <anthony@interlink.com.au>
#
import threading, BaseHTTPServer, SocketServer, urlparse, re, urllib
import socket, time, sys, traceback
import micropubl

def start(adminconf, director):
    AdminClass.director = director
    AdminClass.config = adminconf
    AdminClass.starttime = time.time()
    SocketServer.ThreadingTCPServer.allow_reuse_address = 1
    tcps = SocketServer.ThreadingTCPServer(adminconf.listen, AdminClass)
    at = threading.Thread(target=tcps.serve_forever)
    at.setDaemon(1)
    at.start()

class AdminClass(BaseHTTPServer.BaseHTTPRequestHandler, micropubl.MicroPublisher):
    server_version = "Pydir/0.01"
    director = None
    config = None
    starttime = None
    published_prefix = "pdadmin_"

    def getUser(self, authstr):
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
            return userObj

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
            <div class="title">Python Director version %s, running on host %s.</div>
            """%(self.server_version, socket.gethostname()))

    def footer(self, message=''):
        W = self.wfile.write
        W("""
            <div class="footer">
            <a href="/">top</a>
            <a href="running">running</a>
            <a href="config.xml">config.xml</a>
            <a href="http://pythondirector.sf.net">pythondirector</a>
            </div>""")

        if message:
            message = urllib.unquote(message)
            W("""<p class="message">%s</p>"""%message)
        W("""</body></html>\n\n""")

    def redir(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def action_done(self, mesg):
        self.redir('/running?resultMessage=%s'%urllib.quote(mesg))
        
    def do_GET(self):
        #print "URL",self.path
        h,p,u,p,q,f = urlparse.urlparse(self.path)

        authstr = self.headers.get('Authorization','')
        #print "authstr", authstr
        if authstr:
            user = self.getUser(authstr)
        if not (authstr and user):
            self.unauth(why='no valid auth')
            return

        if u == "/":
            u = 'index_html'

        args = dictify(q)

        if u.startswith("/"):
            u = u[1:]
        u = re.sub(r'\.', '_', u)

        try:
            self.publish(u, args, user=user)
        except micropubl.NotFoundError:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><body>no such URL</body></html>")
        except micropubl.AccessDenied:
            self.unauth('insufficient privileges')
            return 
        except micropubl.uPublisherError:
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><body><h2>error:</h2>")
            e,v,t = sys.exc_info()
            self.wfile.write("<b>%s %s</b>\n<pre>"%(e,v))
            self.wfile.write("\n".join(traceback.format_tb(t)))
            self.wfile.write("</pre>\n</body></html>")

    def pdadmin_pydirector_css(self, Access='Read'):
        self.header(html=0)
        self.wfile.write(PYDIR_CSS)

    def pdadmin_index_html(self, Access='Read'):
        self.header(html=1)
        self.wfile.write("""
            <p>Python Director version %s, running on %s</p>
            <p>Running since %s</p>
            """%(self.server_version,
                 socket.gethostname(),
                 time.ctime(self.starttime)))
        self.footer()

    def pdadmin_running_txt(self, verbose, Access='Read'):
        self.header(html=0)
        W = self.wfile.write
        conf = self.director.conf
        for service in conf.getServices():
            eg = service.getEnabledGroup()
            W('service %s %s %s\n'%(service.name, service.listen, eg.name))
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=verbose)
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

    def pdadmin_running(self, verbose=0, resultmessage='', Access='Read'):
        from urllib import quote
        self.header(html=1)
        W = self.wfile.write
        W("<p><b>current config</b></p>\n")
        conf = self.director.conf
        for service in conf.getServices():
            W('<table><tr><th align="left" colspan="1">Service: %s</th></tr>\n'%
                                                        service.name)
            W('<tr><td colspan="1">Listening on %s</td></tr>\n'%service.listen)
            eg = service.getEnabledGroup()
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=verbose)
                hdict = sch.getHosts()
                if group is eg:
                    klass = 'enabled'
                else:
                    klass = 'inactive'
                W('<tr class="%s"><td colspan="4" class="servHeader">%s '%(klass, group.name))
                if group is eg:
                    W('<b>ENABLED</b>\n')
                else:
                    W('<a href="enableGroup?service=%s&group=%s">enable</a>\n'%
                                            (service.name, group.name))
                W('</td><td valign="top" rowspan="2" class="addWidget">')
                W('<table class="addWidget">')
                W('<form method="GET" action="addHost">')
                W('<input type="hidden" name="service" value="%s">'%service.name)
                W('<input type="hidden" name="group" value="%s">'%group.name)
                W('<tr><td><div class="widgetLabel">name</div></td><td><input name="name" type="text" size="15"></td></tr>')
                W('<tr><td><div class="widgetLabel">ip</div></td><td><input name="ip" type="text" size="15"></td></tr>')
                W('<tr><td colspan=2 align="center"><input type="submit" value="add host"></td></tr>')
                W('</form>')
                W('</table>')
                W('</td>')
                W('</tr>\n')
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
                    W('<td><div class="deleteButton">')
                    a='service=%s&group=%s&ip=%s'%(
                        quote(service.name), quote(group.name), quote(h))
                    W('<a href="delHost?%s">remove host</a>'%(a))
                    W('</div></td>')
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
        self.footer(resultmessage)

    def pdadmin_addHost(self, service, group, name, ip, Access='Write'):
        sched = self.director.getScheduler(serviceName=service, groupName=group)
        sched.newHost(name=name, ip=ip)
        # also add to conf DOM object
        self.action_done('Host %s(%s) added to %s / %s'%(
                name, ip, group, service))
        self.wfile.write("OK\n")

    def pdadmin_delHost(self, service, group, ip, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")

    def pdadmin_delAllHosts(self, service, group, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")

    def pdadmin_enableGroup(self, service, group, Access='Write'):
        self.director.enableGroup(service, group)
        self.action_done('Group %s enabled for service %s'%(
                group, service))
        self.wfile.write("OK\n")

    def pdadmin_changeScheduler(self, service, group, scheduler, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")
        
    def pdadmin_config_xml(self, Access='Write'):
        self.header(html=0)
        self.wfile.write(self.director.conf.dom.toxml())

    def pdadmin_status_txt(self, verbose=0, Access='Read'):
        self.header(html=0)
        W = self.wfile.write
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
        #print "av", av
        a,v = av.split('=',1)
        out[unquote(a)] = unquote(v)
    return out

def html_quote(str):
    return re.subn("<", "&lt;", str)[0]

PYDIR_CSS = """
body {
    font-family: helvetica; 
    font-size: 10pt 
}
a {
    text-decoration: none;
    background-color: transparent;
}

A:link {color: #000000 }
A:visited {color: #000000}
/* borrowed ideas from plone */
div.footer {
    font-family: courier; 
    font-size: 8pt ;
    background: transparent;
    border-collapse: collapse;
    border-top-color: #88AAAA;
    border-top-style: solid;
    border-top-width: 1px;
    padding: 0em 0em 0.5em 2em;
    white-space: nowrap;
    color: #000033 ; 
}

div.footer a {
    background: transparent;
    border-color: #88AAAA;
    border-width: 1px; 
    border-style: none solid solid solid;
    color: #226666;
    font-weight: normal;
    margin-right: 0.5em;
    padding: 0em 2em;
    text-transform: lowercase;
}

div.footer a:hover {
    background: #DEE7EC;
    border-color: #88AAAA;
    border-top-color: #88AAAA;
    color: #436976;
}

div.title { 
    font-weight: bold; 
    color: #000033 ; 
    background: transparent;
    border-color: #88AAAA;
    border-style: none solid solid solid ;
    border-width: 1px;
    margin: 4px;
    padding: 3px;
    white-space: nowrap;
}
div.deleteButton { 
    color: red ; 
    background: yellow;
    border-collapse: collapse;
    border-color: red;
    border-style: solid solid solid solid ;
    border-width: 1px;
    padding: 1px;
    white-space: nowrap;
}

div.deleteButton a {
  color: black;
}

div.deleteButton a:hover {
  color: red;
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


tr.enabled { 
    background-color: #ccdddd; 
    color: #dd0000 
}
tr.inactive { 
    background-color: #eeeeee; 
    color: #000000 
}
tr.inactive td.servHeader a { 
    background-color: #ccdddd; 
    color: #000000 ;
    padding: 0px 2px 0px 2px;
    border-style: solid;
    border-width: 1px;
}
tr.inactive td.servHeader a:hover { 
    background-color: #ccdddd; 
    color: red
}

th {
    font-family: helvetica ; 
    font-size: 10pt ;
}

td { 
    font: 10px helvetica; 

}

td.addWidget {
    padding: 0px;
}
table.addWidget {
    padding: 0px;
}

/*table.addWidget td {
    font: 10px helvetica; 
    background-color: white;
    margin: 0em 0em 0em 0em;
}
*/

div.widgetLabel {
    background-color: transparent;
    font-weight: bold;
    margin: 0em 0em 0em 0em;
}

input {
/* Small cosmetic fix which makes input gadgets look nicer. */
    font: 10px Verdana, Helvetica, Arial, sans-serif;
    border: 1px solid #8cacbb;  
    color: Black;
    background-color: white;
    margin: 0em 0em 0em 0em;
}

input:hover {
   background-color: #DEE7EC ;
}

p.copyright {
    font-weight: bold; 
    max-width: 60%;
}
p.license {
    font-weight: bold; 
    max-width: 60%;
}


"""

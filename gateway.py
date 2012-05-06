from twisted.internet import protocol, reactor
from twisted.web import static, server, proxy
from twisted.web.resource import Resource
import base64, urllib
from os import fork, setsid, umask, dup2
from sys import stdin, stdout, stderr
from os import getpid
from urllib import quote as urlquote

pid_file = "/home/tahoe/gateway/gateway.pid"

modHeaders = {
	'Cache-Control': 'max-age=31536000',
	'Server': 'Cryto-Tahoe-Gateway 1.1',
	'Expires': 'Fri, 12 Dec 2012 05:00:00 GMT'
}


outfile = open(pid_file, 'w')
outfile.write('%i' % getpid())
outfile.close()
if fork(): exit(0)
umask(0) 
setsid() 
if fork(): exit(0)

stdout.flush()
stderr.flush()
si = file('/dev/null', 'r')
so = file('/dev/null', 'a+')
se = file('/dev/null', 'a+', 0)
dup2(si.fileno(), stdin.fileno())
dup2(so.fileno(), stdout.fileno())
dup2(se.fileno(), stderr.fileno())

error_index = ("""\
				<!DOCTYPE html>
				<html>
					<head>
						<title>Cryto-Tahoe-Gateway: Index</title>
					</head>
					<body>
						<h2>This gateway does not provide an index page.</h2>
						Please use a direct URL to download a file hosted on this storage grid.<br><br>
						Alternatively, <a href="http://cryto.net/">learn more about the Cryto Coding Collective</a>.
						<br><br><br><hr>
						<div style="text-align: right; font-style: italic;">Cryto-Tahoe-Gateway v1.1</div>
					</body>
				</html>""")

error_404 = ("""\
				<!DOCTYPE html>
				<html>
					<head>
						<title>Cryto-Tahoe-Gateway: 404</title>
					</head>
					<body>
						<h2>The specified resource was not found.</h2>
						The file may have expired, or the hyperlink you followed may have been broken.<br><br>
						<a href="http://cryto.net/">Learn more about the Cryto Coding Collective</a>.
						<br><br><br><hr>
						<div style="text-align: right; font-style: italic;">Cryto-Tahoe-Gateway v1.1</div>
					</body>
				</html>""")


class ProxyClient(proxy.ProxyClient):
	"""A proxy class that injects headers to the response."""
	def handleEndHeaders(self):
		for key, value in modHeaders.iteritems():
			self.father.responseHeaders.setRawHeaders(key, [value])


class ProxyClientFactory(proxy.ProxyClientFactory):
	protocol = ProxyClient


class ReverseProxyResource(proxy.ReverseProxyResource):
	proxyClientFactoryClass = ProxyClientFactory

	def getChild(self, path, request):
		return ReverseProxyResource(
			self.host, self.port, self.path + '/' + urlquote(path, safe=""))



class GatewayResource(Resource):
	isLeaf = False
	allowedMethods = ("GET")

	def getChild(self, name, request):
		if name == "download":
			try:
				uri = request.path
				uriParts = uri.split('/')
				uriIdentifier = base64.urlsafe_b64decode(uriParts[2])
				fileName = uriParts[3]
				localUri = "/file/" + urllib.quote(uriIdentifier) + "/@@named=/" + urllib.quote(fileName)
				return ReverseProxyResource('localhost', 3456, localUri)
			except:
				return self
		else:
			return self

	def render_GET(self, request):
		path = request.path
		if path == "/":
			return error_index
		else:
			return error_404

resource = GatewayResource()

site = server.Site(resource)
reactor.listenTCP(3719, site)
reactor.run()



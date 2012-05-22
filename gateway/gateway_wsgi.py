"""
    Cryto.net Tahoe-LAFS -> WSGI Gateway Proxy
    --------------------

    Everyone is permitted to copy and distribute verbatim or modified
    copies of this license document, and changing it is allowed as long
    as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
    TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

        0. You just DO WHAT THE FUCK YOU WANT TO.

    This wsgi application's entry point is `app`, you can run it with gunicorn:
        gunicorn gateway:app [options]

    Or you can run it stand-alone:
        python gateway.py [options, --help]


"""

from wsgiref.util import is_hop_by_hop
import base64
import socket
import urllib
import urllib2
import logging
import time

gatewayLog = logging.getLogger("gateway-wsgi")

_config_gatewayTimeout = 15
_config_tahoeServer = 'localhost:3456'
_config_chunkSize = 1 << 13 # 8192, 8kb chunks.

_response_skeleton =\
"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>%(page_title)s</title>
        </head>
        <body>
            <h2>%(page_header)s</h2>
            %(page_text)s<br><br>
            <a href="http://cryto.net/">Learn more about the Cryto Coding Collective</a>.
            <br><br><br><hr>
            <div style="text-align: right; font-style: italic;">Cryto-Tahoe-Gateway v1.1</div>
        </body>
    </html>
"""

def error_404(environ, start_response):
    """
        Returns a 404 page to the client.
    """
    start_response("404 Not Found", [("Content-Type", "text/html")])
    return [_response_skeleton % dict(
        page_title = 'Cryto-Tahoe-Gateway: 404',
        page_header = 'The specified resource was not found.',
        page_text = 'The file may have expired, or the hyperlink you followed may have been broken.'
    )]

def error_500(environ, start_response):
    """
        Returns a 500 page to the client.
    """
    start_response("500 Internal Server Error", [("Content-Type", "text/html")])
    return [_response_skeleton % dict(
        page_title = 'Cryto-Tahoe-Gateway: 500',
        page_header = 'An error has occurred, and the gateway could not process your request, please try again.',
        page_text = ''
    )]

def error_50x(environ, start_response, code = '502', message = "Gateway Timeout"):
    """
        Generic error page... can return any type of error, not only 502.
    """
    start_response("%s %s" % (code, message), [("Content-Type", "text/html")])
    return [_response_skeleton % dict(
        page_title = 'Cryto-Tahoe-Gateway: %s' % code,
        page_header = 'Gateway Error %s: %s'% (code, message),
        page_text = ''
    )]

def index(environ, start_response):
    """
        Generic index.
    """
    start_response("200 OK", [("Content-Type", "text/html")])
    return [_response_skeleton % dict(
        page_title = "Cryto-Tahoe-Gateway: Index",
        page_header = "This gateway does not provide an index page.",
        page_text = "Please use a direct URL to download a file hosted on this storage grid."
    )]

def proxy_pass(environ, start_response):
    """
        Proxy the request to tahoe.
    """

    path = environ['PATH_INFO']
    pathParts = path.split('/')
    if len(pathParts) != 4:
        raise NotFoundError()

    # Convert url to tahoe-type URL.
    _, _, urlIdentifier, fileName = pathParts
    urlIdentifier = urllib.quote(base64.urlsafe_b64decode(urlIdentifier))
    fileName = urllib.quote(fileName)
    localUri = "http://%s/file/%s/@@named=/%s" % (_config_tahoeServer, urlIdentifier, fileName)
    gatewayLog.debug("Proxy passing request (ident: %s, file: %s)", urlIdentifier, fileName)

    # The actual proxying starts here.
    try:
        fp = urllib2.urlopen(localUri, timeout = _config_gatewayTimeout)

    except urllib2.HTTPError, e:

        # Eat any non 200 errors
        gatewayLog.exception("HTTP Error")
        if int(e.code) == 404:
            raise NotFoundError()
        else:
            return error_50x(environ, start_response, e.code, e.msg)

    except urllib2.URLError, e:

        # Something went awry connecting to the backend.
        gatewayLog.exception("Error connecting to backend...")
        try:
            if isinstance(e.args[0], Exception):
                raise e.args[0]
            else:
                raise e
        except socket.timeout:
            return error_50x(environ, start_response, '504', "Gateway Timeout")
        except Exception, e:
            return error_50x(environ, start_response, '503', "Service Unavailable")

    else:

        # Do the actual proxying
        data_sent = 0
        req_start = time.time()
        content_length = fp.info().getheader("Content-Length", 0)

        try:
            response_headers = [(k, v) for k, v in fp.info().items() if not is_hop_by_hop(k)]
            write = start_response("200 OK", response_headers)

            while True:
                chunk = fp.read(_config_chunkSize)
                if not chunk:
                    break
                write(chunk)
                data_sent += len(chunk)

            gatewayLog.debug("Finished proxied request of %s, elapsed: %.02fs, transfer: %s bytes.", fileName,
                time.time() - req_start, data_sent)

        except Exception, e:
            gatewayLog.exception("Error transfering proxied content... %s, sent %s of %s, elapsed %.02f",
                fileName, data_sent, content_length, time.time() - req_start)

        finally:
            fp.close()

    # Wsgi spec says we have to return an empty iterable ._.
    return ()

class NotFoundError(Exception):
    pass

def app(environ, start_response):
    """
        Application entry point, provide me to a wsgi handler!
    """
    try:
        path = environ['PATH_INFO']
        if not path or path == '/':
            return index(environ, start_response)
        elif path.startswith('/download/'):
            return proxy_pass(environ, start_response)
        else:
            raise NotFoundError()

    except NotFoundError:
        return error_404(environ, start_response)

    except Exception, e:
        gatewayLog.exception("WSGI Application encountered error")
        return error_500(environ, start_response)

def main():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-i", '--interface', dest = "interface", help = "interface to bind on", default = "127.0.0.1")
    parser.add_option("-p", '--listen-port', dest = "listen_port", help = "port to listen on", type="int",
        default = 3719)
    parser.add_option("-u", '--tahoe-url', dest = "tahoe_url", help = "address that tahoe is listening on, in form"
                                                                      " host:port", default = 'localhost:3456')
    parser.add_option("-c", '--proxy-chunk-size', dest = "chunk_size", help = "chunk size to read while proxying",
        type = "int", default = 1 << 13)

    parser.add_option("-t", '--gateway-timeout', dest = "gateway_timeout", help = "timeout while connecting to gateway",
        type = "int", default = 15)

    parser.add_option("-d", '--debug', dest = "debug", action = "store_true", default = False,
        help = "debug logging level")

    options, args = parser.parse_args()
    global _config_chunkSize, _config_gatewayTimeout, _config_tahoeServer
    _config_chunkSize = options.chunk_size
    _config_gatewayTimeout = options.gateway_timeout
    _config_tahoeServer = options.tahoe_url

    if options.debug:
        gatewayLog.setLevel(logging.DEBUG)
        logging.basicConfig()

    import wsgiref.simple_server
    wsgiref.simple_server.make_server(options.interface, options.listen_port, app).serve_forever()

if __name__ == '__main__':
    main()

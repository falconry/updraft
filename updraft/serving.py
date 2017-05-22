# -*- coding: utf-8 -*-
"""
    This module is adapted from the werkzeug.serving module, as are several of
    its dependencies.

    :copyright: (c) 2014 by the Werkzeug Team, see COPYRIGHT-NOTICE for more
    details.
    :license: BSD, see COPYRIGHT-NOTICE for more details.
"""

from __future__ import with_statement

import os
import socket
import sys
import signal


try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

from ._internal import _log
from ._compat import reraise, wsgi_encoding_dance
from ._reloader import is_running_from_reloader
from .urls import url_parse, url_unquote
from .middleware import BlanketErrorHandlerMiddleware


class WSGIRequestHandler(BaseHTTPRequestHandler, object):

    """A request handler that implements WSGI dispatching."""

    def make_environ(self):
        request_url = url_parse(self.path)

        def shutdown_server():
            self.server.shutdown_signal = True

        url_scheme = 'http'
        path_info = url_unquote(request_url.path)

        environ = {
            'wsgi.version':         (1, 0),
            'wsgi.url_scheme':      url_scheme,
            'wsgi.input':           self.rfile,
            'wsgi.errors':          sys.stderr,
            'wsgi.multithread':     False,
            'wsgi.multiprocess':    False,
            'wsgi.run_once':        False,
            'werkzeug.server.shutdown': shutdown_server,
            'SERVER_SOFTWARE':      self.server_version,
            'REQUEST_METHOD':       self.command,
            'SCRIPT_NAME':          '',
            'PATH_INFO':            wsgi_encoding_dance(path_info),
            'QUERY_STRING':         wsgi_encoding_dance(request_url.query),
            'CONTENT_TYPE':         self.headers.get('Content-Type', ''),
            'CONTENT_LENGTH':       self.headers.get('Content-Length', ''),
            'REMOTE_ADDR':          self.client_address[0],
            'REMOTE_PORT':          self.client_address[1],
            'SERVER_NAME':          self.server.server_address[0],
            'SERVER_PORT':          str(self.server.server_address[1]),
            'SERVER_PROTOCOL':      self.request_version
        }

        for key, value in self.headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value

        if request_url.netloc:
            environ['HTTP_HOST'] = request_url.netloc

        return environ

    def run_wsgi(self):
        if self.headers.get('Expect', '').lower().strip() == '100-continue':
            self.wfile.write(b'HTTP/1.1 100 Continue\r\n\r\n')

        self.environ = environ = self.make_environ()
        headers_set = []
        headers_sent = []

        def write(data):
            assert headers_set, 'write() before start_response'
            if not headers_sent:
                status, response_headers = headers_sent[:] = headers_set
                try:
                    code, msg = status.split(None, 1)
                except ValueError:
                    code, msg = status, ""
                self.send_response(int(code), msg)
                header_keys = set()
                for key, value in response_headers:
                    self.send_header(key, value)
                    key = key.lower()
                    header_keys.add(key)
                if 'content-length' not in header_keys:
                    self.close_connection = True
                    self.send_header('Connection', 'close')
                if 'server' not in header_keys:
                    self.send_header('Server', self.version_string())
                if 'date' not in header_keys:
                    self.send_header('Date', self.date_time_string())
                self.end_headers()

            assert isinstance(data, bytes), 'applications must write bytes'
            self.wfile.write(data)
            self.wfile.flush()

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        reraise(*exc_info)
                finally:
                    exc_info = None
            elif headers_set:
                raise AssertionError('Headers already set')
            headers_set[:] = [status, response_headers]
            return write

        def execute(app):
            application_iter = app(environ, start_response)
            try:
                for data in application_iter:
                    write(data)
                if not headers_sent:
                    write(b'')
            finally:
                if hasattr(application_iter, 'close'):
                    application_iter.close()
                application_iter = None

        execute(self.server.app)

    def handle(self):
        """Handles a request ignoring dropped connections."""
        rv = None
        try:
            rv = BaseHTTPRequestHandler.handle(self)
        except (socket.error, socket.timeout) as e:
            self.connection_dropped(e)

        if self.server.shutdown_signal:
            self.initiate_shutdown()
        return rv

    def initiate_shutdown(self):
        """A horrible, horrible way to kill the server for Python 2.6 and
        later.  It's the best we can do.
        """
        # Windows does not provide SIGKILL, go with SIGTERM then.
        sig = getattr(signal, 'SIGKILL', signal.SIGTERM)
        # reloader active
        if is_running_from_reloader():
            os.kill(os.getpid(), sig)
        # python 2.7
        self.server._BaseServer__shutdown_request = True
        # python 2.6
        self.server._BaseServer__serving = False

    def connection_dropped(self, error, environ=None):
        """Called if the connection was closed by the client.  By default
        nothing happens.
        """

    def handle_one_request(self):
        """Handle a single HTTP request."""
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
        elif self.parse_request():
            return self.run_wsgi()

    def send_response(self, code, message=None):
        """Send the response header and log the response code."""
        self.log_request(code)
        if message is None:
            message = code in self.responses and self.responses[code][0] or ''
        if self.request_version != 'HTTP/0.9':
            hdr = "%s %d %s\r\n" % (self.protocol_version, code, message)
            self.wfile.write(hdr.encode('ascii'))

    def version_string(self):
        return BaseHTTPRequestHandler.version_string(self).strip()

    def address_string(self):
        return self.environ['REMOTE_ADDR']

    def log_request(self, code='-', size='-'):
        self.log('info', '"%s" %s %s', self.requestline, code, size)

    def log_error(self, *args):
        self.log('error', *args)

    def log_message(self, format, *args):
        self.log('info', format, *args)

    def log(self, type, message, *args):
        _log(type, '%s - - [%s] %s\n' % (self.address_string(),
                                         self.log_date_time_string(),
                                         message % args))


def select_ip_version(host, port):
    """Returns AF_INET4 or AF_INET6 depending on where to connect to."""

    # NOTE(csojinb): This is a holdover comment from Werkzeug that I've kept
    # for reference purposes.
    #
    # disabled due to problems with current ipv6 implementations
    # and various operating systems.  Probably this code also is
    # not supposed to work, but I can't come up with any other
    # ways to implement this.
    # try:
    #     info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
    #                               socket.SOCK_STREAM, 0,
    #                               socket.AI_PASSIVE)
    #     if info:
    #         return info[0][0]
    # except socket.gaierror:
    #     pass
    if ':' in host and hasattr(socket, 'AF_INET6'):
        return socket.AF_INET6
    return socket.AF_INET


class BaseWSGIServer(HTTPServer, object):
    """Simple single-threaded, single-process WSGI server."""
    request_queue_size = 128

    def __init__(self, host, port, app):
        self.address_family = select_ip_version(host, port)
        HTTPServer.__init__(self, (host, int(port)), WSGIRequestHandler)
        self.app = app
        self.shutdown_signal = False

    def log(self, type, message, *args):
        _log(type, message, *args)

    def serve_forever(self):
        self.shutdown_signal = False
        try:
            HTTPServer.serve_forever(self)
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()

    def handle_error(self, request, client_address):
        return HTTPServer.handle_error(self, request, client_address)

    def get_request(self):
        con, info = self.socket.accept()
        return con, info


def run_simple(hostname, port, application, use_reloader=False,
               reloader_interval=1, **kwargs):
    """Start a WSGI application. Optionally auto-reload on code change.

    :param hostname: The host for the application.  eg: ``'localhost'``
    :param port: The port for the server.  eg: ``8080``
    :param application: the WSGI application to execute
    :param use_reloader: should the server automatically restart the python
                         process if modules were changed?
    :param reloader_interval: the interval for the reloader in seconds.
    """
    application = BlanketErrorHandlerMiddleware(application)

    def run_server():
        BaseWSGIServer(hostname, port, application).serve_forever()

    if not is_running_from_reloader():
        display_hostname = hostname != '*' and hostname or 'localhost'
        if ':' in display_hostname:
            display_hostname = '[%s]' % display_hostname
        quit_msg = '(Press CTRL+C to quit)'
        _log('info', ' * Running on http://{}:{}/ {}'.format(
            display_hostname, port, quit_msg))

    if use_reloader:
        # Create and destroy a socket so that any exceptions are raised before
        # we spawn a separate Python interpreter and lose this ability.
        address_family = select_ip_version(hostname, port)
        test_socket = socket.socket(address_family, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_socket.bind((hostname, port))
        test_socket.close()

        from ._reloader import run_with_reloader
        run_with_reloader(run_server, interval=reloader_interval)
    else:
        run_server()

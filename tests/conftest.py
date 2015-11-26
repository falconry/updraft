"""
    This module is adapted from Werkzeug's tests.conftest module.

    :copyright: (c) 2014 by the Werkzeug Team, see COPYRIGHT-NOTICE for more
    details.
    :license: BSD, see COPYRIGHT-NOTICE for more details.
"""

import os
import textwrap
import time
import signal
import sys

import pytest
import requests

from updraft.dev_server import run_dev_server
from updraft.middleware import BasicMiddleware
from updraft._compat import to_bytes


@pytest.fixture
def subprocess(xprocess):
    # NOTE(csojinb): for reasons I don't understand, doing this seems to
    # prevent some test-flakiness
    return xprocess


class PIDMiddleware(BasicMiddleware):

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '/_getpid':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [to_bytes(str(os.getpid()))]
        return self.app(environ, start_response)


def _get_pid_middleware(app):
    return PIDMiddleware(app)


def _dev_server():
    sys.path.insert(0, sys.argv[1])
    import testsuite_app
    app = _get_pid_middleware(testsuite_app.app)
    run_dev_server(app, hostname='localhost', **testsuite_app.kwargs)

if __name__ == '__main__':
    _dev_server()


@pytest.fixture
def test_server(tmpdir, subprocess, request, monkeypatch):
    """
    Returns function that runs a dev server in a separate process for testing.

    :param application: String with contents of module that will be created.
    Module must have a global `app` object. It may optionally have a global
    `kwargs` dict that specifies parameters to pass into the test server.
    """

    class TestServer(object):
        subprocess_name = 'test_server'
        last_pid = None

        def __init__(self, application):
            self.app_pkg = tmpdir.mkdir('testsuite_app')
            self.appfile = self.app_pkg.join('__init__.py')
            self._write_app_to_file(application)
            self._build_server_info()

            self.subprocess = subprocess

        def overwrite_application(self, application):
            self.appfile.remove()
            self._write_app_to_file(application)
            self.wait_for_reloader()

        def request_pid(self):
            for i in range(20):
                time.sleep(0.1 * i)
                try:
                    self.last_pid = int(requests.get(self.url + '/_getpid',
                                                     verify=False).text)
                    return self.last_pid
                except Exception:
                    pass
            return

        def wait_for_reloader(self):
            old_pid = self.last_pid
            for i in range(20):
                time.sleep(0.1 * i)
                new_pid = self.request_pid()
                if not new_pid:
                    raise RuntimeError('Server is down.')
                if self.request_pid() != old_pid:
                    return
            else:
                raise RuntimeError('Server did not reload.')

        def run(self, subprocess):
            subprocess.ensure(
                self.subprocess_name, self.preparefunc, restart=True)

        def teardown(self):
            # NOTE(csojinb): Comment below copied from Werkzeug. Not sure what
            # exactly the problem is with xprocess, but removing this teardown
            # does seem to cause some sort of state leakage between test runs.
            #
            # Killing the process group that runs the server, not just the
            # parent process attached. xprocess is confused about Werkzeug's
            # reloader and won't help here.
            os.killpg(os.getpgid(self.last_pid), signal.SIGTERM)

        def preparefunc(self, cwd):
            # invokes _dev_server() by calling this file as main
            args = [sys.executable, __file__, str(tmpdir)]
            return self.request_pid, args

        def _write_app_to_file(self, application):
            self.appfile.write('\n\n'.join((
                'import falcon',
                'kwargs = dict(port=5001)',
                'app = falcon.API()',
                textwrap.dedent(application),
                "app.add_route('/resource', Resource())"
            )))

        def _build_server_info(self):
            testsuite_app = self._load_app_as_package()
            self.port = testsuite_app.kwargs['port']
            self.addr = 'localhost:{}'.format(self.port)
            self.url = 'http://{}'.format(self.addr)

        def _load_app_as_package(self):
            monkeypatch.delitem(sys.modules, 'testsuite_app', raising=False)
            monkeypatch.syspath_prepend(str(tmpdir))
            import testsuite_app
            return testsuite_app

    def run_test_server(application):
        server = TestServer(application)
        server.run(subprocess)

        request.addfinalizer(server.teardown)

        return server

    return run_test_server

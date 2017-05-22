"""
    This module and test_serving_werkzeug.py both test the functionality in
    dev_server.py. The test_serving_werkzeug.py tests are adapted from
    Werkzeug. The tests here are original updraft work.
"""

import requests
from flaky import flaky


def test_broken_app_returns_500_response(test_server):
    server = test_server(
        """
        class Resource(object):
            def on_get(self, req, resp):
                assert False
        """
    )

    resp = requests.get('http://{}/resource'.format(server.addr))
    assert resp.status_code == 500
    assert 'Internal Server Error' in resp.text


# TODO(csojinb): Figure out why this test flakes and fix it.
@flaky
def test_application_reloads_when_code_changes(test_server):
    app_string = """
        class Resource(object):
            def on_get(self, req, resp):
                resp.status = falcon.HTTP_200
                resp.body = '{}'

        kwargs['use_reloader'] = True
        kwargs['reloader_interval'] = 0.1
    """
    body1 = 'Hello, world!'
    body2 = 'Goodbye, cruel world!'

    server = test_server(app_string.format(body1))
    url = 'http://{}/resource'.format(server.addr)
    resp1 = requests.get(url)

    assert resp1.status_code == 200
    assert resp1.content == body1

    server.overwrite_application(app_string.format(body2))
    resp2 = requests.get(url)

    assert resp2.status_code == 200
    assert resp2.content == body2

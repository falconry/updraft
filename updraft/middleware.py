import pdb

from falcon.errors import HTTPInternalServerError


class BasicMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

    def add_error_handler(self, exception, handler=None):
        return self.app.add_error_handler(exception, handler)


class BlanketErrorHandlerMiddleware(BasicMiddleware):

    """WSGI middleware that returns 500s with tracebacks for uncaught
    application exceptions"""

    def __init__(self, app):
        app.add_error_handler(Exception, self.handle_uncaught_exceptions)
        self.app = app

    @staticmethod
    def handle_uncaught_exceptions(ex, req, resp, params):
        import traceback
        tb = traceback.format_exc()

        raise HTTPInternalServerError(
            title='500 Internal Server Error',
            description=tb)


class PdbDebugMiddleware(BasicMiddleware):

    """WSGI middleware that enables pdb post-mortems for a given application"""

    def __init__(self, app, debug_method=pdb.post_mortem):
        self.debug_method = debug_method
        app.add_error_handler(Exception, self.debug)
        self.app = app

    def debug(self, ex, req, resp, params):
        self.debug_method()
        BlanketErrorHandlerMiddleware.handle_uncaught_exceptions(
            ex, req, resp, params)

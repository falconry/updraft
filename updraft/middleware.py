import pdb


class BasicMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

    def add_error_handler(self, exception, handler=None):
        return self.app.add_error_handler(exception, handler)

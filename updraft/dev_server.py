"""
Unlike serving.py, this file is not directly adapted from Werkzeug. For now, it
functions purely as a passthrough. It is intended as the main entrypoint for
updraft, which can clearly separate original work from Werkzeug-inspired.
"""

from .serving import run_simple


def run_dev_server(api, hostname='127.0.0.1', port=5000, use_reloader=False,
                   reloader_interval=1, use_debugger=False, debug_method=None):
    """Runs a development WSGI server for a falcon application

    Args:
        api: A falcon API object
        hostname (str, optional): The host for the application. Defaults to
            `'127.0.0.1'`
        port (int, optional): The port for the server. Defaults to `5000`
        use_reloader (bool, optional): Should the server automatically restart
            when the application code changes? Defaults to `False`
        reloader_interval (int, optional): Interval (s) at which reloader looks
            for code changes. Defaults to `1`
        use_debugger (bool, optional): Should the server drop you into `pdb` on
            exception? Defaults to `False`
        debug_method (func(), optional): Function that takes no arguments which
            should be run when the application gets an uncaught exception. If
            None (and use_debugger == True), defaults to pdb.post_mortem().

    """
    if use_debugger and debug_method is None:
        import pdb
        debug_method = pdb.post_mortem

    run_simple(hostname, port, api, use_reloader=use_reloader,
               reloader_interval=reloader_interval, use_debugger=use_debugger,
               debug_method=debug_method)

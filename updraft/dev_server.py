"""
Unlike serving.py, this file is not directly adapted from Werkzeug. For now, it
functions purely as a passthrough. It is intended as the main entrypoint for
updraft, which can clearly separate original work from Werkzeug-inspired.
"""

from .serving import run_simple


def run_dev_server(api, hostname='127.0.0.1', port=5000, use_reloader=False,
                   use_debugger=False, reloader_interval=1):
    """Runs a development WSGI server for a falcon application

    Args:
        api: A falcon API object
        hostname (str, optional): The host for the application. Defaults to
            `'127.0.0.1'`
        port (int, optional): The port for the server. Defaults to `5000`
        use_reloader (bool, optional): Should the server automatically restart
            when the application code changes? Defaults to `False`
        use_debugger (bool, optional) [unimplemented]: Should the server drop
            you into `pdb` on exception? Defaults to `False`

    """
    run_simple(hostname, port, api, use_reloader=use_reloader,
               use_debugger=use_debugger, reloader_interval=reloader_interval)

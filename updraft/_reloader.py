"""
    This module is adapted from the werkzeug._reloader module.

    :copyright: (c) 2014 by the Werkzeug Team, see COPYRIGHT-NOTICE for more
    details.
    :license: BSD, see COPYRIGHT-NOTICE for more details.
"""

import os
import sys
import time
import subprocess
import threading
from itertools import chain

from ._internal import _log
from ._compat import PY2, iteritems, text_type


def _iter_module_files():
    """This iterates over all relevant Python files.  It goes through all
    loaded files from modules, all files in folders of already loaded modules
    as well as all files reachable through a package.
    """
    # The list call is necessary on Python 3 in case the module
    # dictionary modifies during iteration.
    for module in [m for m in sys.modules.values() if m is not None]:
        filename = _module_file_or_containing_zip_archive(module)
        if filename is not None:
            yield _clean_compiled_pyfiles(filename)


def _module_file_or_containing_zip_archive(module):
    filename = getattr(module, '__file__', None)
    if not (filename is None or os.path.isfile(filename)):
        filename = _find_zip_archive_path(filename)

    return filename


def _find_zip_archive_path(filename):
    while not os.path.isfile(filename):
        old = filename
        filename = os.path.dirname(filename)
        if filename == old:
            return None

    return filename


def _clean_compiled_pyfiles(filename):
    root, ext = os.path.splitext(filename)
    return filename[:-1] if ext in ('.pyc', '.pyo') else filename


class ReloaderLoop(object):
    name = 'stat'

    # wrapping with `staticmethod` is required in
    # case time.sleep has been replaced by a non-c function (e.g. by
    # `eventlet.monkey_patch`) before we get here
    _sleep = staticmethod(time.sleep)

    def __init__(self, extra_files=None, interval=1):
        self.extra_files = set(
            os.path.abspath(x) for x in extra_files or ())
        self.interval = interval

    def run(self):
        mtimes = {}
        while True:
            for filename in chain(_iter_module_files(), self.extra_files):
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    continue

                old_time = mtimes.get(filename)
                if old_time is None:
                    mtimes[filename] = mtime
                    continue

                elif mtime > old_time:
                    self.trigger_reload(filename)

            self._sleep(self.interval)

    def restart_with_reloader(self):
        """Spawn a new Python interpreter with the same arguments as this one,
        but running the reloader thread.
        """
        while True:
            _log('info', ' * Restarting with %s' % self.name)
            args = [sys.executable] + sys.argv
            new_environ = os.environ.copy()
            new_environ['WERKZEUG_RUN_MAIN'] = 'true'

            # a weird bug on windows. sometimes unicode strings end up in the
            # environment and subprocess.call does not like this, encode them
            # to latin1 and continue.
            if os.name == 'nt' and PY2:
                new_environ = self._encode_latin1(new_environ)

            exit_code = subprocess.call(args, env=new_environ)
            if exit_code != 3:
                return exit_code

    @staticmethod
    def _encode_latin1(environ):
        return dict(
            (key, value.encode(
                'iso-8859-1') if isinstance(value, text_type) else value)
            for key, value in iteritems(environ))

    def trigger_reload(self, filename):
        self.log_reload(filename)
        sys.exit(3)

    def log_reload(self, filename):
        filename = os.path.abspath(filename)
        _log('info', ' * Detected change in %r, reloading' % filename)


def run_with_reloader(main_func, extra_files=None, interval=1):
    """Run the given function in an independent python interpreter."""
    import signal
    reloader = ReloaderLoop(extra_files, interval)
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    try:
        if is_running_from_reloader():
            t = threading.Thread(target=main_func, args=())
            t.setDaemon(True)
            t.start()
            reloader.run()
        else:
            sys.exit(reloader.restart_with_reloader())
    except KeyboardInterrupt:
        pass


def is_running_from_reloader():
    """Check if the application is running from within the reloader subprocess.
    """
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

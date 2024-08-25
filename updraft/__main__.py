import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Run Updraft: Python WSGI/ASGI development server.'
    )
    parser.add_argument('app_module')
    parser.add_argument(
        '-H',
        '--hostname',
        default='127.0.0.1',
        help='hostname to bind to (default: %(default)s)',
    )
    parser.add_argument(
        '-p',
        '--port',
        default=8000,
        type=int,
        help='port to bind to (default: %(default)s)',
    )
    # parser.add_argument('-d', '--use-debugger',
    #                     action='store_true', default=False)
    # parser.add_argument('--no-reload', action='store_false', default=True,
    #                     dest='use_reloader')
    args = parser.parse_args()
    assert args is not None


if __name__ == '__main__':
    main()

import argparse

from dev_server import run_dev_server


def main():
    parser = get_parser()
    kwargs = vars(parser.parse_args())

    module_name = kwargs.pop('module')
    api_name = kwargs.pop('api')

    exec('from {} import {} as api'.format(module_name, api_name))
    run_dev_server(api, **kwargs)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('module')
    parser.add_argument('api')
    parser.add_argument('-H', '--hostname', default='127.0.0.1')
    parser.add_argument('-p', '--port', default=5000, type=int)
    parser.add_argument('-d', '--use-debugger',
                        action='store_true', default=False)
    parser.add_argument('--no-reload', action='store_false', default=True,
                        dest='use_reloader')

    return parser


if __name__ == '__main__':
    main()

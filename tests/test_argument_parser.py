from argparse import Namespace

import pytest

from updraft.__main__ import get_parser


@pytest.fixture(scope='module')
def parser():
    return get_parser()


@pytest.mark.parametrize(('raw_args', 'expected'), [
    (['mythings', 'app'], Namespace(
        module='mythings', api='app', hostname='127.0.0.1', port=5000,
        use_debugger=False, use_reloader=True)),
    (['mythings', 'app', '--port', '7000', '--hostname', '10.1.2.1',
      '--use-debugger', '--no-reload'],
        Namespace(
            module='mythings', api='app', hostname='10.1.2.1', port=7000,
            use_debugger=True, use_reloader=False)),
    (['mythings', 'app', '-p', '7000', '-H', '10.1.2.1', '-d',
      '--no-reload'],
        Namespace(
            module='mythings', api='app', hostname='10.1.2.1', port=7000,
            use_debugger=True, use_reloader=False)),
])
def test_argument_parser(raw_args, expected, parser):
    args = parser.parse_args(raw_args)
    assert args == expected

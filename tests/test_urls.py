# -*- coding: utf-8 -*-
"""
    This module is adapted from Werkzeug's tests.test_urls module.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD, see COPYRIGHT-NOTICE for more details.
"""
from updraft.urls import url_parse, url_unquote


def strict_eq(x, y):
    '''Equality test bypassing the implicit string conversion in Python 2'''
    __tracebackhide__ = True
    assert x == y
    assert issubclass(type(x), type(y)) or issubclass(type(y), type(x))
    if isinstance(x, dict) and isinstance(y, dict):
        x = sorted(x.items())
        y = sorted(y.items())
    elif isinstance(x, set) and isinstance(y, set):
        x = sorted(x)
        y = sorted(y)
    assert repr(x) == repr(y)


def test_parsing():
    url = url_parse('http://127.0.0.1:80/a/b/c?foo=bar#baz')
    assert url.scheme == 'http'
    assert url.netloc == '127.0.0.1:80'
    assert url.path == '/a/b/c'
    assert url.query == 'foo=bar'
    assert url.fragment == 'baz'


def test_quoting():
    strict_eq(url_unquote('%C3%B6%C3%A4%C3%BC'), u'\xf6\xe4\xfc')

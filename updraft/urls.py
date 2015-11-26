# -*- coding: utf-8 -*-
"""
    This module is adapted from the werkzeug.serving module, as are several of
    its dependencies.

    ``updraft.urls`` used to provide several wrapper functions for Python 2
    urlparse, whose main purpose were to work around the behavior of the Py2
    stdlib and its lack of unicode support. While this was already a somewhat
    inconvenient situation, it got even more complicated because Python 3's
    ``urllib.parse`` actually does handle unicode properly. In other words,
    this module would wrap two libraries with completely different behavior. So
    now this module contains a 2-and-3-compatible backport of Python 3's
    ``urllib.parse``, which is mostly API-compatible.

    :copyright: (c) 2014 by the Werkzeug Team, see COPYRIGHT-NOTICE for more
    details.
    :license: BSD, see COPYRIGHT-NOTICE for more details.
"""
import os
import re
from collections import namedtuple

from ._compat import (
    text_type, to_native, make_literal_wrapper, fix_tuple_repr)


# A regular expression for what a valid scheme looks like
_scheme_re = re.compile(r'^[a-zA-Z0-9+-.]+$')

# Characters that are safe in any part of an URL.
_always_safe = (b'abcdefghijklmnopqrstuvwxyz'
                b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-+')

_hexdigits = '0123456789ABCDEFabcdef'
_hextobyte = dict(
    ((a + b).encode(), int(a + b, 16))
    for a in _hexdigits for b in _hexdigits
)


URLTuple = fix_tuple_repr(namedtuple(
    'URLTuple', ['scheme', 'netloc', 'path', 'query', 'fragment']))


def _unquote_to_bytes(string, unsafe=''):
    if isinstance(string, text_type):
        string = string.encode('utf-8')
    if isinstance(unsafe, text_type):
        unsafe = unsafe.encode('utf-8')
    unsafe = frozenset(bytearray(unsafe))
    bits = iter(string.split(b'%'))
    result = bytearray(next(bits, b''))
    for item in bits:
        try:
            char = _hextobyte[item[:2]]
            if char in unsafe:
                raise KeyError()
            result.append(char)
            result.extend(item[2:])
        except KeyError:
            result.extend(b'%')
            result.extend(item)
    return bytes(result)


def url_parse(url, scheme=None, allow_fragments=True):
    """Parses a URL from a string into a :class:`URL` tuple.  If the URL
    is lacking a scheme it can be provided as second argument. Otherwise,
    it is ignored.  Optionally fragments can be stripped from the URL
    by setting `allow_fragments` to `False`.

    The inverse of this function is :func:`url_unparse`.

    :param url: the URL to parse.
    :param scheme: the default schema to use if the URL is schemaless.
    :param allow_fragments: if set to `False` a fragment will be removed
                            from the URL.
    """
    s = make_literal_wrapper(url)
    # is_text_based = isinstance(url, text_type)

    if scheme is None:
        scheme = s('')
    netloc = query = fragment = s('')
    i = url.find(s(':'))
    if i > 0 and _scheme_re.match(to_native(url[:i], errors='replace')):
        # make sure "iri" is not actually a port number (in which case
        # "scheme" is really part of the path)
        rest = url[i + 1:]
        if not rest or any(c not in s('0123456789') for c in rest):
            # not a port number
            scheme, url = url[:i].lower(), rest

    if url[:2] == s('//'):
        delim = len(url)
        for c in s('/?#'):
            wdelim = url.find(c, 2)
            if wdelim >= 0:
                delim = min(delim, wdelim)
        netloc, url = url[2:delim], url[delim:]
        if (s('[') in netloc and s(']') not in netloc) or \
           (s(']') in netloc and s('[') not in netloc):
            raise ValueError('Invalid IPv6 URL')

    if allow_fragments and s('#') in url:
        url, fragment = url.split(s('#'), 1)
    if s('?') in url:
        url, query = url.split(s('?'), 1)

    return URLTuple(scheme, netloc, url, query, fragment)


def url_unquote(string, charset='utf-8', errors='replace', unsafe=''):
    """URL decode a single string with a given encoding.  If the charset
    is set to `None` no unicode decoding is performed and raw bytes
    are returned.

    :param s: the string to unquote.
    :param charset: the charset of the query string.  If set to `None`
                    no unicode decoding will take place.
    :param errors: the error handling for the charset decoding.
    """
    rv = _unquote_to_bytes(string, unsafe)
    if charset is not None:
        rv = rv.decode(charset, errors)
    return rv

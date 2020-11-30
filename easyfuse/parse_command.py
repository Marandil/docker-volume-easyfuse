'''
easyfuse - simple FUSE volume driver for Docker
Copyright (C) 2020  Marcin Słowik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import itertools
import os
import re
import shlex

# Can be removed >= Python 3.9
from typing import List, Union, Mapping

MappingType = Mapping[str, str]


class ParserError(Exception):
    pass


def _append_mapping(lst, token, mapping):
    value = mapping.get(token, '')
    if '\n' in value:
        value = list(value.split('\n'))
    elif value:
        value = [value]
    else:
        value = []
    lst.append(value)


def parse_command(command: str, mapping: MappingType):
    parser = shlex.shlex(command, punctuation_chars=True)
    cmd: List[List[str]] = []
    sub: List[List[str]] = None
    while True:
        token = parser.get_token()
        if token == parser.eof:
            break
        elif token == ']':
            if sub is None:
                raise ParserError("misplaced ]")
            cmd += itertools.product(*sub)
            sub = None
        elif token == '[':
            if sub is not None:
                raise ParserError("nested [")
            sub = []
        elif token == '{':
            varname = parser.get_token()
            if varname == parser.eof:
                raise ParserError("invalid {variable} token")
            token = parser.get_token()
            if token != '}':
                raise ParserError("missing }")
            _append_mapping(sub if sub is not None else cmd, varname, mapping)
        elif sub is not None:
            sub.append([token])
        else:
            cmd.append([token])
    if sub is not None:
        raise ParserError("unterminated [")
    return [y for x in cmd for y in x]

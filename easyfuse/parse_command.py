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
import shlex

# Can be removed >= Python 3.9
from typing import List, Mapping

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
    """
    Parse POSIX-style shell command line into tokens, replacing values in { } with values
    from mapping. Mapping values are split on newlines, i.e. lists should be passed as
    newline-delimited strings. All values in [ ] are repeated for cross-product of such
    lists. Empty strings create no value / empty list. I.e. for command "[-o {value}]",
    if value is "", an empty list is returned; if value is "value", ["-o", "value"] is
    returned; if value is "v1\nv2", the result is ["-o", "v1", "-o", "v2"].
    The resulting list can be fed directly to `subprocess.run` or similar.
    :param command: string containing input command in POSIX-style shell format (+[] and {}
                    as described above)
    :param mapping: str -> str mapping containing at least all { } variables from command.
    :returns:       list of parsed and substituted tokens.
    """
    parser = shlex.shlex(command, punctuation_chars=True, posix=True)
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

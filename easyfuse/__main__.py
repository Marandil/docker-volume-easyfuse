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

import aiohttp.web
import argparse
import logging
import os
import socket

from .Driver import Driver
from .Handler import Handler


def main(opts):
    """
    Main entrypoint for the docker volume plugin service.
    :param opts:  Namespace containing at least the following fields:
                   * systemd: bool - if True, the service is started as socket activated and attempts
                     to listen on fd 3.
                   * host: str, port: int, path: str (may be None) - passed directly to aiohttp if not
                     running in systemd socket activated mode.
                  The remaining options are consumed by the :class:`Driver`.
    """
    logging.basicConfig(level=logging.INFO)
    app = aiohttp.web.Application()
    driver = Driver(opts)
    handler = Handler(driver)
    handler.install(app)
    if opts.systemd:
        SD_LISTEN_FDS_START = 3
        sock = socket.fromfd(SD_LISTEN_FDS_START, socket.AF_UNIX, socket.SOCK_STREAM)
        aiohttp.web.run_app(app, sock=sock)
    else:
        aiohttp.web.run_app(app, host=opts.host, port=opts.port, path=opts.sock)


if __name__ == '__main__':
    DEFAULT_PORT = os.environ.get('EASYFUSE_SOCK_PORT', None)
    DEFAULT_HOST = os.environ.get('EASYFUSE_SOCK_HOST', None)
    DEFAULT_SOCK = os.environ.get('EASYFUSE_UNIX_SOCK', None)
    DEFAULT_MOUNT_PATH = os.environ.get('EASYFUSE_MOUNT_PATH', "/run/easyfuse/mntpt")
    DEFAULT_MOUNT_DB = os.environ.get('EASYFUSE_MOUNT_DB', "/run/easyfuse/mntdb.json")

    argparser = argparse.ArgumentParser('easyfuse',
                                        description="""
        Simple FUSE-based docker volume driver based on the local driver
        syntax.
        """,
                                        epilog="""
        Default argument values are taken from corresponding environment
        variables. PORT/HOST/SOCK arguments are passed directly to the
        built-in aiohttp server, meaning all-None configuration results in a
        0.0.0.0:8080 server.

        Use of Unix socket is recommended.

        When using systemd socket activation (-S | --systemd), PORT/HOST/SOCK
        arguments are ignored.
        """)
    argparser.add_argument("-p",
                           "--port",
                           default=DEFAULT_PORT,
                           type=int,
                           help="TCP port to bind to "
                           f"(default: {DEFAULT_PORT} [EASYFUSE_SOCK_PORT])")
    argparser.add_argument("-b",
                           "--host",
                           default=DEFAULT_HOST,
                           type=str,
                           help="TCP host to bind to "
                           f"(default: {DEFAULT_HOST} [EASYFUSE_SOCK_HOST])")
    argparser.add_argument("-s",
                           "--sock",
                           default=DEFAULT_SOCK,
                           type=str,
                           help="UNIX socket to bind to "
                           f"(default: {DEFAULT_SOCK} [EASYFUSE_UNIX_SOCK])")
    argparser.add_argument("-S",
                           "--systemd",
                           default=False,
                           action='store_true',
                           help="use fd 3 (SD_LISTEN_FDS_START); "
                           "used for systemd socket activation")
    argparser.add_argument("-m",
                           "--mntpt",
                           default=DEFAULT_MOUNT_PATH,
                           type=str,
                           help="base mount point; if exists, must be writeable "
                           f"(default: {DEFAULT_MOUNT_PATH} [EASYFUSE_MOUNT_PATH])")
    argparser.add_argument("-d",
                           "--mntdb",
                           default=DEFAULT_MOUNT_DB,
                           type=str,
                           help="mount database location; the location must be writeable "
                           f"(default: {DEFAULT_MOUNT_DB} [EASYFUSE_MOUNT_DB])")
    args = argparser.parse_args()
    main(args)

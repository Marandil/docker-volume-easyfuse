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

import os
import subprocess

from .MountDatabase import MountDatabase, VolumeSpec


class DriverError(Exception):
    pass


class Driver:
    def __init__(self, opts):
        self.mntpath = opts.mntpt
        self.mntdb = MountDatabase(opts.mntdb)
        dbpath = os.path.dirname(opts.mntdb)
        os.makedirs(self.mntpath, mode=0o777, exist_ok=True)
        os.makedirs(dbpath, mode=0o777, exist_ok=True)

    def get_path_for(self, name: str):
        return os.path.join(self.mntpath, name)

    async def is_mounted(self, name):
        async with self.mntdb:
            return self.mntdb.get_ro(name).is_mounted

    @property
    async def volumes(self):
        """
        Provides a read-only view of the mntdb
        """
        async with self.mntdb:
            return {key: self.mntdb.get_ro(key) for key in self.mntdb.keys()}

    async def volume_create(self, name: str, opts: dict):
        async with self.mntdb:
            if name in self.mntdb:
                raise DriverError(
                    f"Volume {name} already exist, remove it first.")
            self.mntdb[name] = VolumeSpec(name, set(), opts)

    async def volume_remove(self, name: str):
        async with self.mntdb:
            del self.mntdb[name]

    async def volume_mount(self, name: str, vid: str):
        async with self.mntdb:
            try:
                vol = self.mntdb[name]
            except KeyError:
                raise DriverError(f"Volume {name} not found.")
            vol.instances.add(vid)
            if not vol.is_mounted:
                # mount -t fuse -o [opts.o] [opts.device] [mountpoint]
                cmd = ("mount", "-t", "fuse")
                try:
                    cmd += ("-o", vol.opts["o"])
                except KeyError:
                    pass
                try:
                    cmd += (vol.opts["device"], )
                except KeyError:
                    raise DriverError(f"Volume {name} missing option: device")
                mntpt = self.get_path_for(name)
                cmd += (mntpt, )
                try:
                    os.makedirs(mntpt, mode=0o777, exist_ok=True)
                    subprocess.run(cmd, check=True)
                    vol.is_mounted = True
                except subprocess.CalledProcessError as e:
                    raise DriverError(e)

    async def volume_unmount(self, name: str, vid: str):
        async with self.mntdb:
            try:
                vol = self.mntdb[name]
            except KeyError:
                raise DriverError(f"Volume {name} not found.")
            try:
                vol.instances.remove(vid)
            except KeyError:
                raise DriverError(f"Volume ID {vid} not found.")
            if not vol.instances and vol.is_mounted:
                mntpt = self.get_path_for(name)
                try:
                    cmd = ('umount', mntpt)
                    subprocess.run(cmd, check=True)
                    vol.is_mounted = False
                except subprocess.CalledProcessError as e:
                    raise DriverError(e)

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

from .MountDatabase import MountDatabase, VolumeSpec, MountOptions
from .parse_command import parse_command, MappingType


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
            try:
                return self.mntdb[name].is_mounted
            except KeyError:
                raise DriverError(f"Volume {name} not found.")

    @property
    async def volumes(self):
        """
        Provides a read-only view of the mntdb
        """
        async with self.mntdb:
            return {key: self.mntdb[key] for key in self.mntdb.keys()}

    async def volume_create(self, name: str, opts: dict):
        async with self.mntdb:
            if name in self.mntdb:
                raise DriverError(f"Volume {name} already exist, remove it first.")
            mount_opts = MountOptions(**opts)
            self.mntdb[name] = VolumeSpec(name, [], mount_opts)

    async def volume_remove(self, name: str):
        async with self.mntdb:
            try:
                del self.mntdb[name]
            except KeyError:
                raise DriverError(f"Volume {name} not found.")

    def _get_opts(self, vol) -> MappingType:
        return {
            "opts": vol.opts.opts,
            "driver": vol.opts.driver,
            "target": self.get_path_for(vol.name),
            "device": vol.opts.device,
        }

    async def volume_mount(self, name: str, vid: str):
        async with self.mntdb:
            try:
                vol = self.mntdb[name]
            except KeyError:
                raise DriverError(f"Volume {name} not found.")
            if vid not in vol.instances:
                vol.instances.append(vid)
            if not vol.is_mounted:
                mapping = self._get_opts(vol)
                cmd = parse_command(vol.opts.mount_command, mapping)
                os.makedirs(mapping['target'], mode=0o777, exist_ok=True)
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    raise DriverError(e)
                vol.is_mounted = True

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
                mapping = self._get_opts(vol)
                cmd = parse_command(vol.opts.unmount_command, mapping)
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    raise DriverError(e)
                os.rmdir(mapping['target'])
                vol.is_mounted = False

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

import asyncio
import dataclasses
import json
import logging

# Can be removed >= Python 3.9
from typing import Set

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class MountOptions:
    device: str
    opts: str = ''
    driver: str = 'fuse'
    mount_command: str = 'mount -t {driver} [-o {opts}] {device} {target}'
    unmount_command: str = 'umount {target}'


@dataclasses.dataclass
class VolumeSpec:
    name: str
    instances: list
    opts: MountOptions
    is_mounted: bool = False


class DatabaseJSONEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        super().__init__(sort_keys=True, **kwargs)

    def default(self, obj: object):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


class DatabaseJSONDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        super().__init__(object_hook=self._object_hook, **kwargs)

    def _object_hook(self, obj: dict):
        if VolumeSpec.__annotations__.keys() == obj.keys():
            return VolumeSpec(**obj)
        elif MountOptions.__annotations__.keys() == obj.keys():
            return MountOptions(**obj)
        return obj


class MountDatabase:
    def __init__(self, dbpath: str):
        self._lock = asyncio.Lock()
        self._path = dbpath
        self._encoder = DatabaseJSONEncoder()
        self._decoder = DatabaseJSONDecoder()
        self._db: dict = None
        self._dbhash: int = 0
        self._dirty: dict = None

    async def __aenter__(self):
        await self._lock.acquire()
        try:
            with open(self._path, 'r') as fdb:
                s = fdb.read()
            self._db = self._decoder.decode(s)
            logger.debug(f"Loaded mntdb {self._path} -> {s}")
        except FileNotFoundError:
            s = "{}"
            self._db = {}
            logger.debug(f"mntdb {self._path} not found -> {s}")
        self._dbhash = hash(s)
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        s = self._encoder.encode(self._db)
        if hash(s) != self._dbhash:
            logger.debug(f"Saving mntdb {self._path} <- {s}")
            with open(self._path, 'w') as fdb:
                fdb.write(s)
        self._db = None
        self._lock.release()

    def __contains__(self, key) -> bool:
        return key in self._db

    def __getitem__(self, key) -> VolumeSpec:
        return self._db[key]

    def keys(self) -> Set[str]:
        return set(self._db.keys())

    def __setitem__(self, key, value: VolumeSpec) -> VolumeSpec:
        self._db[key] = value
        return value

    def __delitem__(self, key):
        del self._db[key]

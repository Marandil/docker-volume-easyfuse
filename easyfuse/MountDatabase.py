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
from typing import Dict, Set

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class VolumeSpec:
    name: str
    instances: set
    opts: dict
    is_mounted: bool = False


class MountDatabase:
    def __init__(self, dbpath: str):
        self._lock = asyncio.Lock()
        self._path = dbpath
        self._db: dict = None
        self._dbhash: int = 0
        self._dirty: dict = None

    async def __aenter__(self):
        await self._lock.acquire()
        try:
            with open(self._path, 'r') as fdb:
                s = fdb.read()
            self._db = json.loads(s)
            logger.debug(f"Loaded mntdb {self._path} -> {s}")
        except FileNotFoundError:
            s = "{}"
            self._db = {}
            logger.debug(f"mntdb {self._path} not found -> {s}")
        self._dbhash = hash(s)
        self._dirty = dict()

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        for key, entry in self._dirty.items():
            try:
                db_entry = self._db[key]
            except KeyError:
                db_entry = self._db[key] = {}
            self._update_db(db_entry, entry)
        s = json.dumps(self._db, sort_keys=True)
        if hash(s) != self._dbhash:
            logger.debug(f"Saving mntdb {self._path} <- {s}")
            with open(self._path, 'w') as fdb:
                fdb.write(s)
        self._db = None
        self._lock.release()
        self._dirty = None

    def __contains__(self, key):
        return key in self._db

    def __getitem__(self, key) -> VolumeSpec:
        try:
            return self._dirty[key]
        except KeyError:
            db_entry = self._db[key]
            self._dirty[key] = spec = self._read_db(db_entry)
            return spec

    def get_ro(self, key) -> VolumeSpec:
        """ Same as __getitem__, but doesn't mark the entry as "dirty" and therefore
        doesn't require updating all entries on exit when all volumes are only read. """
        try:
            return self._dirty[key]
        except KeyError:
            return self._read_db(self._db[key])

    def keys(self) -> Set[str]:
        return set(self._dirty.keys() | self._db.keys())

    def __setitem__(self, key, value: VolumeSpec):
        self._dirty[key] = value

    def __delitem__(self, key):
        del self._db[key]

    def _read_db(self, db_entry: dict) -> VolumeSpec:
        return VolumeSpec(
            name=db_entry['name'],
            instances=set(db_entry['instances']),
            opts=db_entry['opts'],
            is_mounted=db_entry['is_mounted'])

    def _update_db(self, db_entry: dict, value: VolumeSpec):
        db_entry['name'] = value.name
        db_entry['instances'] = list(value.instances)
        db_entry['opts'] = value.opts
        db_entry['is_mounted'] = value.is_mounted

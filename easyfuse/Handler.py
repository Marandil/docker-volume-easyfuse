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
import json
import logging

from .Driver import Driver, DriverError
from .parse_command import ParserError

logger = logging.getLogger(__name__)


def _jsonify(obj, **kwargs):
    """
    Convert `obj` to json and then to aiohttp `Response` object, passing the given `kwargs` to its
    constructor.
    :param obj: Any default json-convertible object.
    :param kwargs: Collection of named arguments, passed down to aiohttp `Response`.
    """
    return aiohttp.web.Response(text=json.dumps(obj), **kwargs)


class Handler:
    def __init__(self, driver: Driver):
        self.driver = driver

    async def handle_plugin_activate(self, request: aiohttp.web.Request):
        return _jsonify({"Implements": ["VolumeDriver"]})

    async def handle_volumedriver_create(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            opts = body['Opts']
            await self.driver.volume_create(name, opts)
            return _jsonify({"Err": ""})
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except DriverError as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_remove(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            await self.driver.volume_remove(name)
            return _jsonify({"Err": ""})
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except DriverError as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_mount(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            vid = body['ID']
            await self.driver.volume_mount(name, vid)
            return _jsonify({"Mountpoint": self.driver.get_path_for(name), "Err": ""})
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except (DriverError, ParserError) as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_path(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            return _jsonify({"Mountpoint": self.driver.get_path_for(name), "Err": ""})
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except DriverError as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_unmount(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            vid = body['ID']
            await self.driver.volume_unmount(name, vid)
            return _jsonify({"Err": ""})
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except (DriverError, ParserError) as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_get(self, request: aiohttp.web.Request):
        try:
            body = await request.json()
            logger.info(f"{request.path} -> {body}")
            name = body['Name']
            return _jsonify({
                "Volume": {
                    "Name": name,
                    "Mountpoint": self.driver.get_path_for(name),
                    "Status": {
                        "Mounted": await self.driver.is_mounted(name)
                    }
                },
                "Err": ""
            })
        except KeyError as e:
            return _jsonify({"Err": f"Missing option: {e}"}, status=400)
        except DriverError as e:
            return _jsonify({"Err": str(e)}, status=400)

    async def handle_volumedriver_list(self, request: aiohttp.web.Request):
        logger.info(request.path)
        return _jsonify({
            "Volumes": [{
                "Name": name,
                "Mountpoint": self.driver.get_path_for(name)
            } for name in await self.driver.volumes],
            "Err":
            ""
        })

    async def handle_volumedriver_capabilities(self, request: aiohttp.web.Request):
        logger.info(request.path)
        return _jsonify({"Capabilities": {"Scope": "global"}})

    def install(self, app: aiohttp.web.Application):
        app.add_routes([
            aiohttp.web.post('/Plugin.Activate', self.handle_plugin_activate),
            aiohttp.web.post('/VolumeDriver.Create', self.handle_volumedriver_create),
            aiohttp.web.post('/VolumeDriver.Remove', self.handle_volumedriver_remove),
            aiohttp.web.post('/VolumeDriver.Mount', self.handle_volumedriver_mount),
            aiohttp.web.post('/VolumeDriver.Path', self.handle_volumedriver_path),
            aiohttp.web.post('/VolumeDriver.Unmount', self.handle_volumedriver_unmount),
            aiohttp.web.post('/VolumeDriver.Get', self.handle_volumedriver_get),
            aiohttp.web.post('/VolumeDriver.List', self.handle_volumedriver_list),
            aiohttp.web.post('/VolumeDriver.Capabilities', self.handle_volumedriver_capabilities),
        ])

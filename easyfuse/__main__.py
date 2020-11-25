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
import dataclasses
import json
import os
import subprocess


def jsonify(obj, **kwargs):
    return aiohttp.web.Response(text=json.dumps(obj), **kwargs)


@dataclasses.dataclass
class VolumeSpec:
    name: str
    instances: set
    opts: dict
    is_mounted: bool = False


class DriverError(Exception):
    pass


class Driver:
    def __init__(self):
        self.volumes: dict[str, VolumeSpec] = {}
        self._path = "/run/docker-easyfuse"
        os.makedirs(self._path, mode=0o777, exist_ok=True)

    def get_path_for(self, name: str):
        return os.path.join(self._path, name)

    def volume_create(self, name: str, opts: dict):
        if name in self.volumes:
            raise DriverError(f"Volume {name} already exist, remove it first.")
        self.volumes[name] = VolumeSpec(name, set(), opts)

    def volume_remove(self, name: str):
        del self.volumes[name]

    def volume_mount(self, name: str, vid: str):
        try:
            vol = self.volumes[name]
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
            os.makedirs(mntpt, mode=0o777, exist_ok=True)
            subprocess.run(cmd, check=True)
            vol.is_mounted = True

    def volume_unmount(self, name: str, vid: str):
        try:
            vol = self.volumes[name]
        except KeyError:
            raise DriverError(f"Volume {name} not found.")
        try:
            vol.instances.remove(vid)
        except KeyError:
            raise DriverError(f"Volume ID {vid} not found.")
        if not vol.instances and vol.is_mounted:
            mntpt = self.get_path_for(name)
            cmd = ('umount', mntpt)
            subprocess.run(cmd, check=True)
            vol.is_mounted = False


class Handler:
    def __init__(self, driver: Driver):
        self.driver = driver

    async def handle_plugin_activate(self, request):
        return jsonify({"Implements": ["VolumeDriver"]})

    async def handle_volumedriver_create(self, request):
        try:
            body = await request.json()
            name = body['Name']
            opts = body['Opts']
            self.driver.volume_create(name, opts)
            return jsonify({"Err": ""})
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_remove(self, request):
        try:
            body = await request.json()
            name = body['Name']
            self.driver.volume_remove(name)
            return jsonify({"Err": ""})
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_mount(self, request):
        try:
            body = await request.json()
            name = body['Name']
            vid = body['ID']
            self.driver.volume_mount(name, vid)
            return jsonify({
                "Mountpoint": self.driver.get_path_for(name),
                "Err": ""
            })
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_path(self, request):
        try:
            body = await request.json()
            name = body['Name']
            return jsonify({
                "Mountpoint": self.driver.get_path_for(name),
                "Err": ""
            })
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_unmount(self, request):
        try:
            body = await request.json()
            name = body['Name']
            vid = body['ID']
            self.driver.volume_unmount(name, vid)
            return jsonify({"Err": ""})
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_get(self, request):
        try:
            body = await request.json()
            name = body['Name']
            print(name)
            return jsonify({
                "Volume": {
                    "Name": name,
                    "Mountpoint": self.driver.get_path_for(name),
                    "Status": {
                        "Mounted": self.driver.volumes[name].is_mounted
                    }
                },
                "Err": ""
            })
        except KeyError as e:
            return jsonify({"Err": f"Missing option: {e}"})
        except DriverError as e:
            return jsonify({"Err": str(e)})

    async def handle_volumedriver_list(self, request):
        return jsonify({
            "Volumes": [{
                "Name": name,
                "Mountpoint": self.driver.get_path_for(name)
            } for name in self.driver.volumes],
            "Err":
            ""
        })

    async def handle_volumedriver_capabilities(self, request):
        return jsonify({"Capabilities": {"Scope": "global"}})


app = aiohttp.web.Application()
driver = Driver()
handler = Handler(driver)
app.add_routes([
    aiohttp.web.post('/Plugin.Activate', handler.handle_plugin_activate),
    aiohttp.web.post('/VolumeDriver.Create',
                     handler.handle_volumedriver_create),
    aiohttp.web.post('/VolumeDriver.Remove',
                     handler.handle_volumedriver_remove),
    aiohttp.web.post('/VolumeDriver.Mount', handler.handle_volumedriver_mount),
    aiohttp.web.post('/VolumeDriver.Path', handler.handle_volumedriver_path),
    aiohttp.web.post('/VolumeDriver.Unmount',
                     handler.handle_volumedriver_unmount),
    aiohttp.web.post('/VolumeDriver.Get', handler.handle_volumedriver_get),
    aiohttp.web.post('/VolumeDriver.List', handler.handle_volumedriver_list),
    aiohttp.web.post('/VolumeDriver.Capabilities',
                     handler.handle_volumedriver_capabilities),
])

if __name__ == '__main__':
    aiohttp.web.run_app(app)

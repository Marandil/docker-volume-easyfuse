import asyncio
import json
import pathlib
import shlex
import shutil
import sys
import unittest

from argparse import Namespace
from easyfuse.Driver import DriverError, Driver


class TestDriver(unittest.TestCase):
    def setUp(self):
        here = pathlib.Path(__file__).parent.resolve()
        self.testdir = here / '.test'
        self.mntpt = self.testdir / 'mntpt'
        self.mntdb = self.testdir / 'mntdb.json'
        opts = Namespace(mntpt=str(self.mntpt), mntdb=str(self.mntdb))
        self.driver = Driver(opts)
        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def test_get_path_for(self):
        self.assertEqual(str(self.mntpt / 'vol'),
                         self.driver.get_path_for('vol'))

    def test_volume_create(self):
        self.loop.run_until_complete(self._test_volume_create())

    async def _test_volume_create(self):
        await self.driver.volume_create('vol', {
            'device': '~device',
            'opts': '~opts'
        })
        with self.mntdb.open('r') as f:
            d = json.load(f)
        self.assertIn('vol', d)
        self.assertIn('opts', d['vol'])
        self.assertIn('name', d['vol'])
        self.assertIn('instances', d['vol'])
        self.assertIn('is_mounted', d['vol'])

        self.assertIn('driver', d['vol']['opts'])
        self.assertIn('device', d['vol']['opts'])
        self.assertIn('opts', d['vol']['opts'])
        self.assertEqual(d['vol']['opts']['driver'], 'fuse')
        self.assertEqual(d['vol']['opts']['device'], '~device')
        self.assertEqual(d['vol']['opts']['opts'], '~opts')

        self.assertEqual(d['vol']['name'], 'vol')
        self.assertEqual(d['vol']['instances'], [])
        self.assertEqual(d['vol']['is_mounted'], False)

    def test_volume_remove(self):
        self.loop.run_until_complete(self._test_volume_remove())

    async def _test_volume_remove(self):
        await self.driver.volume_create('vol', {
            'device': '~device',
            'opts': '~opts'
        })
        await self.driver.volume_remove('vol')
        with self.mntdb.open('r') as f:
            d = json.load(f)
        self.assertFalse(d)

    def test_volume_mount_unmount(self):
        self.loop.run_until_complete(self._test_volume_mount_unmount())

    async def _test_volume_mount_unmount(self):
        # we use python as mount command, with the following command as device
        # to dump the remaining arguments to file
        dc = 'import sys; open(sys.argv[1], "w").write(repr(sys.argv[2:]))'
        await self.driver.volume_create('vol', {'device': dc, 'opts': '~opts'})
        with self.mntdb.open('r') as f:
            d = json.load(f)
        dropfile_a = self.testdir / "drop-a"
        d['vol']['opts']['mount_command'] = (
            f'{sys.executable} -c {{device}} '
            f'{str(dropfile_a)} {{target}} {{opts}} {{driver}}')
        dropfile_b = self.testdir / "drop-b"
        d['vol']['opts']['unmount_command'] = (
            f'{sys.executable} -c {{device}} '
            f'{str(dropfile_b)} {{target}} {{opts}} {{driver}}')
        with self.mntdb.open('w') as f:
            json.dump(d, f)
        args = [str(self.mntpt / 'vol'), "~opts", "fuse"]
        await self.driver.volume_mount('vol', 'ffffffffffffffff')
        self.assertTrue(await self.driver.is_mounted('vol'))
        await self.driver.volume_unmount('vol', 'ffffffffffffffff')
        self.assertFalse(await self.driver.is_mounted('vol'))
        with dropfile_a.open('r') as f:
            self.assertEqual(f.read(), repr(args))
        with dropfile_b.open('r') as f:
            self.assertEqual(f.read(), repr(args))

    def test_volume_missing_errors(self):
        self.loop.run_until_complete(self._test_volume_missing_errors())

    async def _test_volume_missing_errors(self):
        with self.assertRaises(DriverError) as ctx:
            await self.driver.is_mounted('vol')
        self.assertEqual(str(ctx.exception), 'Volume vol not found.')
        with self.assertRaises(DriverError) as ctx:
            await self.driver.volume_remove('vol')
        self.assertEqual(str(ctx.exception), 'Volume vol not found.')
        with self.assertRaises(DriverError) as ctx:
            await self.driver.volume_mount('vol', 'ffff')
        self.assertEqual(str(ctx.exception), 'Volume vol not found.')
        with self.assertRaises(DriverError) as ctx:
            await self.driver.volume_unmount('vol', 'ffff')
        self.assertEqual(str(ctx.exception), 'Volume vol not found.')

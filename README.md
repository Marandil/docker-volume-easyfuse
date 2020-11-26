# `easyfuse` - simple FUSE volume driver for Docker

Simple FUSE-based docker volume driver based on the local driver systax. By offloading volume mounting to a simple `mount -t fuse` subprocess call, the typical problem of https://github.com/moby/moby/issues/27103 does not apply.

The plugin uses legacy architecture (mounting as a unix socket) to expose to the user full host system capabilites of `mount`. This way, user can e.g. fully specify `uid` and `gid` volume mapping, use local system resources (e.g. SSH keys), something that is an annoying shortcoming of plugins such as `vieux/sshfs`.

Initially, the plugin was developed to allow using SSHFS in scenario, where `vieux/sshfs` simply wouldn't work, and after discovering _why_ the `local` driver would not work with fuse mount type. Hovever, in theory this plugin should work with any `fuse`-mounted filesystem (and in future, possibly even others).

### Permissions

Currently, since easyfuse uses `mount` for creating actual fuse volumes, `easyfuse` must be ran as root. This may change in future versions.

## Package dependencies

It's relatively easy to run `easyfuse` without actually installing the package, nevertheless it 
requires some non-standard third party Python libraries. To start, simply install module dependencies 
(see [requirements.txt]), either with

```
sudo python3 -m pip install -r requirements.txt
```

or (preferably) with your system package manager, e.g. for Debian/Ubuntu:

```
sudo apt install python3-aiohttp
```

When using `pip`, make sure the packages are installed globally, as `easyfuse` currently needs to be ran as root.

## Local installation in virtual environment

`easyfuse` should have no problems working out of a python virtual environment.
Simply initialize a virtual environment and install the package locally:

```
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -e .
```

This will pull all local requirements, without interfering with the system and system's package
managers.

When running from venv with `sudo`, you may need to manually point to the venv's python as virtual
environment variables are not inherited by `sudo`-ed process, see:

```
# locally installed aiohttp in version 3.5.1, venv installed aiohttp in version 3.7.3:
(venv) $ python3 -c 'import aiohttp; print(aiohttp.__version__)'
3.7.3
(venv) $ sudo python3 -c 'import aiohttp; print(aiohttp.__version__)'
3.5.1
```

Instead, simply use `venv/bin/python` explicitly:

```
(venv) $ sudo venv/bin/python -c 'import aiohttp; print(aiohttp.__version__)'
3.7.3
```

## Running manually (without installation)

To run in a stand-alone mode (preferred for development), start in the main directory and simply run

```
sudo python3 -m easyfuse -s /run/docker/plugins/easyfuse.sock
```

see `python3 -m easyfuse -h` (no `sudo` required) for full list of available options.

## Running with `systemd` (with or without installation)

`systemd` folder contains basic systemd unit files for socket activation, either for global and local
setup.
Assuming `/etc/systemd/system` as the configuration path of choice, typical activation for a local setup would be:

```
$ SYSTEMD_UNIT_TARGET=/etc/systemd/system
$ sudo cp systemd/easyfuse.socket $SYSTEMD_UNIT_TARGET/
$ WORKDIR=$PWD envsubst '$WORKDIR' < systemd/easyfuse.service.dev | sudo tee $SYSTEMD_UNIT_TARGET/easyfuse.service
$ sudo systemctl daemon-reload
$ sudo systemctl start easyfuse.socket
```

When using virtualenv, use the appropriate config:

```
(venv) $ SYSTEMD_UNIT_TARGET=/etc/systemd/system
(venv) $ sudo cp systemd/easyfuse.socket $SYSTEMD_UNIT_TARGET/
(venv) $ envsubst '$VIRTUAL_ENV' < systemd/easyfuse.service.venv | sudo tee $SYSTEMD_UNIT_TARGET/easyfuse.service
(venv) $ sudo systemctl daemon-reload
(venv) $ sudo systemctl start easyfuse.socket
```

For a global installation (i.e. if you can call `python3 -m easyfuse -h` as root from anywhere, without virtual environment), simply use:

```
$ SYSTEMD_UNIT_TARGET=/etc/systemd/system
$ sudo cp systemd/easyfuse.socket  $SYSTEMD_UNIT_TARGET/
$ sudo cp systemd/easyfuse.service $SYSTEMD_UNIT_TARGET/
$ sudo systemctl daemon-reload
$ sudo systemctl start easyfuse.socket
```

## Using `easyfuse` with docker volume

Note: when using SSHFS, make sure the host key is accepted by the root user (or whatever user is running the mount command). This can be done by simply doing `sudo ssh user@my-ssh-host` and verifying the public key, or with `ssh-keyscan >> /root/.ssh/known_hosts`.

```
$ docker volume create -d easyfuse -o 'o=IdentityFile=$HOME/.ssh/id_ed25519,uid=1000,gid=1000,users,idmap=user,noatime,allow_other,_netdev,reconnect,rw' -o 'device=sshfs#user@my-ssh-host:/my-ssh-volume' my-volume
my-volume
```

```
$ docker run --rm -it -v my-volume:/my-volume busybox ls /my-volume -lah
total 8K
drwxrwsr-x    1 1000     1000        4.0K Nov 25 00:43 .
drwxr-xr-x    1 root     root        4.0K Nov 25 13:27 ..
```

```
$ docker volume rm my-volume
my-volume
```

## Using `easyfuse` with docker-compose

A fully-featured example with docker-compose can be found in the examples folder. See also [below](#verify-with-docker-compose).

```
volumes:
  nfs:
    driver: easyfuse
    driver_opts:
      o: IdentityFile=$PWD/my-secret.key,uid=1000,gid=1000,users,idmap=user,noatime,allow_other,_netdev,reconnect,rw
      device: "sshfs#testuser@localhost:testdir"
```

## Test with minimal local sshfs setup

Folder examples/mini-sshfs contains a minimal sshd configuration and startup script for your local user that you can use to test the plugin.

The scripts assume you have sshd available at /usr/sbin/sshd. This can be easily overriden with SSHD environment variable. To start the server simply issue:

```
examples$ mini-sshfs/run_sshd.sh
```

The script will generate user and host keys and store them locally in the mini-sshfs folder. The server runs at port 2022 (override with MINI_SSHD_PORT environment variable) and binds to localhost interfaces only (127.0.0.1 and ::1). To verify the server works you can check if ssh with the exported known_hosts and user key work:

```
examples$ ssh -o UserKnownHostsFile=mini-sshfs/known_hosts -i mini-sshfs/.keys/ssh_user_ed25519_key -p 2022 $USER@localhost
Last login: Wed Nov 25 00:00:00 2020 from xx.yy.zz.ww

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
$ exit
logout
Connection to localhost closed.
examples$
```

### Verify with a regular named volume

```
examples$ docker volume create -d easyfuse -o "o=IdentityFile=$PWD/mini-sshfs/.keys/ssh_user_ed25519_key,UserKnownHostsFile=$PWD/mini-sshfs/known_hosts,port=2022,uid=1000,gid=1000,users,idmap=user,noatime,allow_other,_netdev,reconnect,rw" -o "device=sshfs#$USER@localhost:$PWD/test" my-volume
my-volume

examples$ docker run --rm -it -v my-volume:/my-volume busybox ls /my-volume -lah
total 12K
drwxr-xr-x    1 1000     1000        4.0K Nov 25 15:16 .
drwxr-xr-x    1 root     root        4.0K Nov 25 15:45 ..
-rw-r--r--    1 1000     1000         445 Nov 25 15:17 lorem_ipsum.txt

examples$ docker volume rm my-volume
my-volume
```

### Verify with docker-compose

```
examples$ cat docker-compose.yml
version: '3.4'

services:
  mytest:
    image: alpine
    volumes:
      - 'nas:/nas:rw'
    command: [sh, -c, 'touch /nas/test; ls -lah /nas;']

volumes:
  nas:
    driver: easyfuse
    driver_opts:
      o: IdentityFile=$PWD/mini-sshfs/.keys/ssh_user_ed25519_key,UserKnownHostsFile=$PWD/mini-sshfs/known_hosts,Port=2022,uid=1000,gid=1000,users,idmap=user,noatime,allow_other,_netdev,reconnect,rw
      device: "sshfs#$USER@localhost:$PWD/test"

examples$ docker-compose up
Creating volume "examples_nas" with easyfuse driver
Starting examples_mytest_1 ... done
Attaching to examples_mytest_1
mytest_1  | total 12K
mytest_1  | drwxr-xr-x    1 1000     1000        4.0K Nov 25 16:29 .
mytest_1  | drwxr-xr-x    1 root     root        4.0K Nov 25 16:29 ..
mytest_1  | -rw-r--r--    1 1000     1000         445 Nov 25 15:17 lorem_ipsum.txt
mytest_1  | -rw-r--r--    1 1000     1000           0 Nov 25 16:29 test
examples_mytest_1 exited with code 0

examples$ docker-compose down -v
Removing examples_mytest_1 ... done
Removing network examples_default
Removing volume examples_nas
```

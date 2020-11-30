# Running with `systemd`

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

## Automatic systemd setup

`easyfuse` provides a simple automatic `systemd` setup via `easyfuse.systemd_setup` script-module. 
See `python3 -m easyfuse.systemd_setup -h` for reference. Remember that when using `sudo` with `venv`,
you need to use the `venv` symlink instead of `python3`:

```
(venv) $ sudo python3 -m easyfuse.systemd_setup venv          # <- this will install using the global python
(venv) $ sudo venv/bin/python3 -m easyfuse.systemd_setup venv # <- this will install using the local venv
```

# Package setup and dependencies

You can now install the package directly from PyPI with:

```
$ python3 -m pip install docker-volume-easyfuse
```

or from GitHub with:

```
$ python3 -m pip install git+https://github.com/Marandil/docker-volume-easyfuse
```

Setup inside virtual environment is also possible. More setup options are listed below.

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


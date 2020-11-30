import argparse
import pathlib
import pkg_resources
import subprocess
import sys


def setup(systemd_unit_dir: pathlib.Path, setup_type: str):
    if setup_type not in ('global', 'venv', 'local'):
        raise ValueError(f"Invalid setup type: {setup_type}, " "allowed options are global, venv, local")

    socket_file = pkg_resources.resource_string(__name__, 'systemd/easyfuse.socket')
    with (systemd_unit_dir / 'easyfuse.socket').open('wb') as fout:
        fout.write(socket_file)

    if setup_type == 'global':
        service_file = pkg_resources.resource_string(__name__, 'systemd/easyfuse.service')
    elif setup_type == 'venv':
        service_file = pkg_resources.resource_string(__name__, 'systemd/easyfuse.service.venv')
        service_file = service_file.replace(b'$VIRTUAL_ENV', sys.prefix.encode())
    elif setup_type == 'local':
        service_file = pkg_resources.resource_string(__name__, 'systemd/easyfuse.service.dev')
        here = pathlib.Path(__file__).parent.parent.resolve()
        service_file = service_file.replace(b'$WORKDIR', str(here).encode())
    with (systemd_unit_dir / 'easyfuse.service').open('wb') as fout:
        fout.write(service_file)


def enable():
    subprocess.run(('systemctl', 'daemon-reload'), check=True)
    subprocess.run(('systemctl', 'enable', 'easyfuse.socket'), check=True)
    subprocess.run(('systemctl', 'restart', 'easyfuse.socket'), check=True)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('type',
                           choices=['local', 'global', 'venv'],
                           help="choose which context should be used to call the module")
    argparser.add_argument('-p',
                           '--path',
                           type=pathlib.Path,
                           default=pathlib.Path('/etc/systemd/system'),
                           help="choose where to store systemd unit files; see systemd.unit(5); "
                           "default is /etc/systemd/system")
    argparser.add_argument('-e',
                           '--enable',
                           action='store_true',
                           help="use systemctl to reload and enable the socket service")
    args = argparser.parse_args()
    setup(args.path, args.type)
    if args.enable:
        enable()

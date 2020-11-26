from setuptools import find_packages, setup
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='easyfuse',
    version='0.2.0',
    description='simple FUSE volume driver for Docker',
    long_description=long_description,
    long_description_content_type='text/markdown',

    author="Marcin Słowik",
    author_email="me@marandil.pl",

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'aiohttp'
    ],
    python_requires='>=3.6',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
)

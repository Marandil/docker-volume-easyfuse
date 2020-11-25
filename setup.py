from setuptools import find_packages, setup
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='easyfuse',
    version='0.1.0',
    description='simple FUSE volume driver for Docker',
    long_description=long_description,
    long_description_content_type='text/markdown',

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'aiohttp'
    ],
)

#!/usr/bin/env python3
"""
The packaging script.

Example:

    python3 setup.py sdist bdist_wheel
"""
import os
import sys
import warnings
from pathlib import Path

from setuptools import setup

import proxytest

if sys.version_info < (3, 4):
    warnings.warn('Python 3.4 or above is recommended!')

base_path = str(Path(__file__).parent.absolute())

# use README as the long description (not the right markup, but good enough)
with open(os.path.join(base_path, 'README.md'), "r") as fh:
    long_description = fh.read()

# Python3.4 requires the `typing` backports
install_requires = [
    'typing>=3.6.0,<4.0; python_version<"3.5.0"'
]

# requirements for optional backends, e.g. pip install proxytest[aiohttp]
extras_require = {
    'aiohttp': ['aiohttp'],
    'requests': ['requests'],
}

# install all packaged backends: pip install proxytest[all]
all_extra_requires = [name for requires in extras_require.values()
                      for name in requires]
extras_require['all'] = sorted(set(all_extra_requires))

setup(
        name='proxytest',
        version=proxytest.__version__,
        description='A simple script to test if one or more HTTP proxies are '
                    'working by fetching a webpage.',
        long_description=long_description,
        classifiers=[
            "Environment :: Console",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
        ],
        keywords='proxy test command multiple proxies',
        author='Oleg Pryadko',
        author_email='oleg@olegpryadko.com',
        maintainer='Oleg Pryadko',
        maintainer_email='oleg@olegpryadko.com',
        url='https://github.com/yoleg/proxytest',
        license='MIT',
        packages=[
            'proxytest',
            'proxytest.backends',
            'proxytest.backends.aiohttp',
        ],
        entry_points={
            'console_scripts': [
                'proxytest = proxytest.proxytest:run_from_command_line',
            ]
        },
        install_requires=install_requires,
        extras_require=extras_require,
)

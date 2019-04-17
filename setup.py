#!/usr/bin/env python3
import os
import sys
import warnings

from setuptools import setup, find_packages
import proxytest

if sys.version_info < (3, 5):
    warnings.warn('Python 3.5 or above is recommended!')

with open(os.path.join(os.path.dirname(__file__), 'README.md'), "r") as fh:
    long_description = fh.read()

install_requires = [
    'aiohttp>=3.5.4,<4.0; python_version>="3.5.3"',
    'requests>=2.21.0,<3.0; python_version<"3.5.3"',
    'typing>=3.6.6,<4.0; python_version<"3.5.3"'
]

setup(
    name='proxytest',
    version=proxytest.__version__,
    description='A simple script to test if one or more HTTP proxies are working by fetching a webpage.',
    long_description=long_description,
    classifiers=[
        "Environment :: Console",
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
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'proxytest = proxytest.proxytest:main',
        ]
    },
    install_requires=install_requires,
)

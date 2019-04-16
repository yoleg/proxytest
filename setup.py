#!/usr/bin/env python3
import sys
from setuptools import setup, find_packages
import proxytest

if sys.version_info < (3, 4):
    raise Exception('Python 3.4 or above required!')

setup(
    name='proxytest',
    version=proxytest.__version__,
    description='A simple script to test if one or more proxies are working by fetching a webpage.',
    long_description='',
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
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'proxytest = proxytest.proxytest:main',
        ]
    },
    install_requires=['requests'],
)

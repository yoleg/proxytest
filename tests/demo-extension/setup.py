from setuptools import setup

import proxytest

setup(
        name="proxytest-demo-extension",
        version=proxytest.__version__,
        # package name MUST be "proxytest.backends" for the namespace package to work
        packages=['proxytest.backends'],
)

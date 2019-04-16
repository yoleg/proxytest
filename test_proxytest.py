#!/usr/bin/env python3
""" Tests for proxytest. """
import unittest

from proxytest.proxytest import process_proxy_string


class proxytestTestCase(unittest.TestCase):
    def test_process_proxy_string(self):
        proxies = list(process_proxy_string('1.2.3.4:5678-5680'))
        self.assertEqual(proxies, ['1.2.3.4:5678', '1.2.3.4:5679', '1.2.3.4:5680'])


if __name__ == '__main__':
    unittest.main()

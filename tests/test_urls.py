#!/usr/bin/env python3
""" Tests for proxytest. """
import unittest

from proxytest.urls import expand_proxy_url


class ProxyTestURLsTestCase(unittest.TestCase):
    def test_process_proxy_string(self):
        proxies = list(expand_proxy_url('1.2.3.4:5678-5680'))
        self.assertEqual(proxies, ['http://1.2.3.4:5678', 'http://1.2.3.4:5679', 'http://1.2.3.4:5680'])

        proxies = list(expand_proxy_url('user@1.2.3.4:5679-5680'))
        self.assertEqual(proxies, ['http://user@1.2.3.4:5679', 'http://user@1.2.3.4:5680'])

        proxies = list(expand_proxy_url('us-er:pa-s--s@1.2.3.4:5679-5680'))
        self.assertEqual(proxies, ['http://us-er:pa-s--s@1.2.3.4:5679', 'http://us-er:pa-s--s@1.2.3.4:5680'])

        proxies = list(expand_proxy_url('http://us-er:pa-s--s@1.2.3.4:5679-5680'))
        self.assertEqual(proxies, ['http://us-er:pa-s--s@1.2.3.4:5679', 'http://us-er:pa-s--s@1.2.3.4:5680'])

        proxies = list(expand_proxy_url('https://us-er:pa-s--s@1.2.3.4:5679-5680'))
        self.assertEqual(proxies, ['https://us-er:pa-s--s@1.2.3.4:5679', 'https://us-er:pa-s--s@1.2.3.4:5680'])

        proxies = list(expand_proxy_url('https://us-er:pa-s--s@1.2.3.4:5679'))
        self.assertEqual(proxies, ['https://us-er:pa-s--s@1.2.3.4:5679'])

        proxies = list(expand_proxy_url('https://us-er:pa-s--s@1.2.3.4'))
        self.assertEqual(proxies, ['https://us-er:pa-s--s@1.2.3.4:8080'])

        proxies = list(expand_proxy_url('us-er:pa-s--s@1.2.3.4'))
        self.assertEqual(proxies, ['http://us-er:pa-s--s@1.2.3.4:8080'])

        proxies = list(expand_proxy_url(':@1.2.3.4'))
        self.assertEqual(proxies, ['http://:@1.2.3.4:8080'])

        proxies = list(expand_proxy_url(':@1.2.3.4:'))
        self.assertEqual(proxies, ['http://:@1.2.3.4:8080'])

        with self.assertRaises(ValueError):
            list(expand_proxy_url(':@1.2.3.4::'))

        with self.assertRaises(ValueError):
            list(expand_proxy_url(''))


if __name__ == '__main__':
    unittest.main()

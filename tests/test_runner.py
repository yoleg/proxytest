#!/usr/bin/env python3
""" Tests for proxytest.Runner class. """
import unittest
from typing import List

from demo_extension import activate_demo_extension, deactivate_demo_extension
from proxytest import backend, proxytest


class RunnerTestCase(unittest.TestCase):

    def _run_runner(self, args: List[str]):
        parser = proxytest.get_argument_parser()
        options = parser.parse_args(args)
        runner = proxytest.Runner(options)
        runner.run()
        return runner

    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(backend.reset_backends)
        self.addCleanup(deactivate_demo_extension)
        activate_demo_extension()
        backend.find_backends()

    def test_runner_success(self):
        runner = self._run_runner(['1.2.3.4:1234', '1.2.3.4:1234', '--backend=dummy-success'])
        self.assertFalse(runner.running)
        self.assertEqual(runner.ran_count, 2)
        self.assertEqual(runner.failed_count, 0)

    def test_runner_error(self):
        runner = self._run_runner(['1.2.3.4:1234', '1.2.3.4:1234', '--backend=dummy-error'])
        self.assertFalse(runner.running)
        self.assertEqual(runner.ran_count, 2)
        self.assertEqual(runner.failed_count, 2)

    def test_runner_unfinished(self):
        with self.assertRaises(proxytest.UnableToTest):
            self._run_runner(['1.2.3.4:1234', '1.2.3.4:1234', '--backend=dummy-unfinished'])

    def test_runner_unstarted(self):
        with self.assertRaises(proxytest.UnableToTest):
            self._run_runner(['1.2.3.4:1234', '1.2.3.4:1234', '--backend=dummy-unfinished'])


if __name__ == '__main__':
    unittest.main()

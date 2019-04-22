""" Entry point for calling with python -m proxytest ... """

import sys

from . import run_from_command_line

sys.exit(run_from_command_line())

# This file is required to add tests dir to pythonpath for pytest
# https://github.com/pytest-dev/pytest/issues/2421
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

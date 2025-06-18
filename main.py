#!/usr/bin/env python3
"""
Legacy entry point for the LMU Configuration Editor.
Redirects to the main package entry point.
"""

import sys
from json_lmu_editor.main import main

if __name__ == "__main__":
    sys.exit(main())

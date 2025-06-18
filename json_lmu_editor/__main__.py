#!/usr/bin/env python3
"""
Package entry point for json_lmu_editor.

Allows running the package with: python -m json_lmu_editor
"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())

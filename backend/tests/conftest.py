"""
Pytest configuration and shared fixtures for MiroFish backend tests.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path so imports work
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

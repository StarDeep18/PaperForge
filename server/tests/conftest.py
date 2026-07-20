"""
Pytest global configuration and module mocks.
"""

import sys
from unittest.mock import MagicMock

# Mock chromadb globally to allow tests to compile and run offline/locally
# without needing C++ Build Tools for hnswlib compilation.
mock_chroma = MagicMock()
mock_chroma.config = MagicMock()
mock_chroma.config.Settings = MagicMock()

sys.modules["chromadb"] = mock_chroma
sys.modules["chromadb.config"] = mock_chroma.config

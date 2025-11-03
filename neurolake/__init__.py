"""
NeuroLake: AI-Native Data Platform with NCF Storage Format

World's first data platform with neural compression and learned indexes.

Copyright 2025 NeuroLake
"""

__version__ = "0.1.0-alpha"
__author__ = "NeuroLake Team"

# Expose main modules
from neurolake.ncf import NCFWriter, NCFReader, NCFSchema

__all__ = [
    "NCFWriter",
    "NCFReader",
    "NCFSchema",
    "__version__",
]

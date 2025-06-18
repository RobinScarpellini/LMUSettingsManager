"""
Performance optimization modules for the LMU Configuration Editor.
"""

from .lazy_loader import LazyLoader, lazy_component
from .search_indexer import SearchIndexer, SearchResult

__all__ = ["LazyLoader", "lazy_component", "SearchIndexer", "SearchResult"]

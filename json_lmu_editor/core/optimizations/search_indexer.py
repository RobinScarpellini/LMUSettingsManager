"""
Search indexing system for fast configuration field searching.

Provides efficient search capabilities with pre-built indices and fuzzy matching.
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import time

from ..models.configuration_model import ConfigurationModel


@dataclass
class SearchResult:
    """Represents a search result."""

    field_path: str
    field_name: str
    category: str
    match_type: str  # 'name', 'description', 'value'
    relevance_score: float
    matched_text: str
    context: str = ""


class TrieNode:
    """Node in a trie data structure for prefix searching."""

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.is_end_of_word = False
        self.field_paths: Set[str] = set()
        self.word_count = 0


class SearchTrie:
    """Trie data structure for efficient prefix searching."""

    def __init__(self):
        self.root = TrieNode()
        self.logger = logging.getLogger(__name__)

    def insert(self, word: str, field_path: str) -> None:
        """
        Insert a word into the trie.

        Args:
            word: Word to insert
            field_path: Associated field path
        """
        word = word.lower().strip()
        if not word:
            return

        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            node.field_paths.add(field_path)

        node.is_end_of_word = True
        node.word_count += 1

    def search_prefix(self, prefix: str) -> Set[str]:
        """
        Search for all field paths that contain words with the given prefix.

        Args:
            prefix: Prefix to search for

        Returns:
            Set of field paths
        """
        prefix = prefix.lower().strip()
        if not prefix:
            return set()

        node = self.root
        for char in prefix:
            if char not in node.children:
                return set()
            node = node.children[char]

        # Collect all field paths from this node and its children
        return self._collect_field_paths(node)

    def _collect_field_paths(self, node: TrieNode) -> Set[str]:
        """Recursively collect all field paths from a node."""
        paths = node.field_paths.copy()

        for child in node.children.values():
            paths.update(self._collect_field_paths(child))

        return paths


@dataclass
class SearchIndex:
    """Complete search index for configuration fields."""

    name_trie: SearchTrie
    description_trie: SearchTrie
    value_trie: SearchTrie
    field_data: Dict[str, Dict[str, Any]]
    category_mapping: Dict[str, str]
    word_to_fields: Dict[str, Set[str]]
    last_updated: float


class SearchIndexer:
    """Builds and maintains search indices for fast searching."""

    def __init__(self):
        """Initialize the search indexer."""
        self.logger = logging.getLogger(__name__)
        self.index: Optional[SearchIndex] = None
        self.index_build_time = 0.0

        # Search configuration
        self.min_word_length = 2
        self.max_results = 100
        self.fuzzy_threshold = 0.6

        # Word extraction pattern
        self.word_pattern = re.compile(r"\b\w{2,}\b", re.IGNORECASE)

        # Cache for recent searches
        self.search_cache: Dict[str, List[SearchResult]] = {}
        self.cache_max_size = 50

    def build_index(self, config_model: ConfigurationModel) -> SearchIndex:
        """
        Build search index from configuration model.

        Args:
            config_model: Configuration model to index

        Returns:
            Built search index
        """
        start_time = time.time()
        self.logger.info("Building search index...")

        name_trie = SearchTrie()
        description_trie = SearchTrie()
        value_trie = SearchTrie()
        field_data = {}
        category_mapping = {}
        word_to_fields = defaultdict(set)

        # Index all fields
        field_count = 0
        for field_path, field_state in config_model.field_states.items():
            field_info = config_model.get_field_info(field_path)
            if not field_info:
                continue

            field_count += 1
            category = field_info.category
            # Extract field name from path (last part after the dot)
            field_name = field_path.split(".")[-1] if "." in field_path else field_path
            description = field_info.description or ""
            value = str(field_info.value) if field_info.value is not None else ""

            # Store field data
            field_data[field_path] = {
                "name": field_name,
                "description": description,
                "value": value,
                "category": category,
                "type": field_info.type.value if field_info.type else "unknown",
            }

            category_mapping[field_path] = category

            # Index field name
            name_words = self._extract_words(field_name)
            for word in name_words:
                name_trie.insert(word, field_path)
                word_to_fields[word].add(field_path)

            # Index description
            if description:
                desc_words = self._extract_words(description)
                for word in desc_words:
                    description_trie.insert(word, field_path)
                    word_to_fields[word].add(field_path)

            # Index value (for searchable values)
            if value and len(value) <= 100:  # Don't index very long values
                value_words = self._extract_words(value)
                for word in value_words:
                    value_trie.insert(word, field_path)
                    word_to_fields[word].add(field_path)

        # Create index
        self.index = SearchIndex(
            name_trie=name_trie,
            description_trie=description_trie,
            value_trie=value_trie,
            field_data=field_data,
            category_mapping=category_mapping,
            word_to_fields=dict(word_to_fields),
            last_updated=time.time(),
        )

        self.index_build_time = time.time() - start_time
        self.logger.info(
            f"Search index built in {self.index_build_time:.3f}s for {field_count} fields"
        )

        # Clear search cache when index is rebuilt
        self.search_cache.clear()

        return self.index

    def update_index_incremental(self, changes: List[str]) -> None:
        """
        Update search index incrementally for changed fields.

        Args:
            changes: List of field paths that changed
        """
        if not self.index:
            self.logger.warning("No index to update")
            return

        # For now, we rebuild the entire index on changes
        # A more sophisticated implementation could update specific entries
        self.logger.debug(f"Incremental update requested for {len(changes)} fields")
        # TODO: Implement true incremental updates

    def search_with_index(self, query: str) -> List[SearchResult]:
        """
        Search using the built index.

        Args:
            query: Search query

        Returns:
            List of search results sorted by relevance
        """
        if not self.index:
            self.logger.warning("No search index available")
            return []

        query = query.strip().lower()
        if len(query) < self.min_word_length:
            return []

        # Check cache first
        if query in self.search_cache:
            self.logger.debug(f"Returning cached results for '{query}'")
            return self.search_cache[query]

        start_time = time.time()

        # Extract search terms
        search_terms = self._extract_words(query)
        if not search_terms:
            return []

        # Collect matching field paths
        matching_fields = set()

        # Search in names (highest priority)
        for term in search_terms:
            name_matches = self.index.name_trie.search_prefix(term)
            matching_fields.update(name_matches)

        # Search in descriptions
        for term in search_terms:
            desc_matches = self.index.description_trie.search_prefix(term)
            matching_fields.update(desc_matches)

        # Search in values (lower priority)
        for term in search_terms:
            value_matches = self.index.value_trie.search_prefix(term)
            matching_fields.update(value_matches)

        # Create search results
        results = []
        for field_path in matching_fields:
            if field_path not in self.index.field_data:
                continue

            field_data = self.index.field_data[field_path]
            result = self._create_search_result(
                field_path, field_data, query, search_terms
            )
            if result:
                results.append(result)

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Limit results
        results = results[: self.max_results]

        # Cache results
        if len(self.search_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.search_cache))
            del self.search_cache[oldest_key]

        self.search_cache[query] = results

        search_time = time.time() - start_time
        self.logger.debug(
            f"Search for '{query}' completed in {search_time:.3f}s, {len(results)} results"
        )

        return results

    def _extract_words(self, text: str) -> List[str]:
        """
        Extract searchable words from text.

        Args:
            text: Text to extract words from

        Returns:
            List of words
        """
        if not text:
            return []

        words = self.word_pattern.findall(text.lower())
        return [word for word in words if len(word) >= self.min_word_length]

    def _create_search_result(
        self,
        field_path: str,
        field_data: Dict[str, Any],
        query: str,
        search_terms: List[str],
    ) -> Optional[SearchResult]:
        """
        Create a search result for a field.

        Args:
            field_path: Field path
            field_data: Field data from index
            query: Original search query
            search_terms: Extracted search terms

        Returns:
            SearchResult or None
        """
        field_name = field_data["name"]
        value = field_data["value"]
        category = field_data["category"]

        # Determine match type and calculate relevance
        match_type = ""
        relevance_score = 0.0
        matched_text = ""
        context = ""

        # Check name match (highest relevance)
        name_lower = field_name.lower()
        if any(term in name_lower for term in search_terms):
            match_type = "name"
            relevance_score = 100.0
            matched_text = field_name

            # Exact match gets higher score
            if query in name_lower:
                relevance_score = 150.0

            # Match at beginning gets higher score
            if name_lower.startswith(query):
                relevance_score = 200.0

        # Check value match (lower relevance)
        elif value and any(term in value.lower() for term in search_terms):
            match_type = "value"
            relevance_score = 50.0
            matched_text = value
            context = f"Value: {value}"

        else:
            # No direct match found, this shouldn't happen with our indexing
            return None

        # Boost score based on category popularity or other factors
        if "graphics" in category.lower() or "dx11" in category.lower():
            relevance_score *= 1.1  # Graphics settings are commonly searched

        # Boost score for shorter field names (more likely to be exact matches)
        if len(field_name) <= 20:
            relevance_score *= 1.05

        return SearchResult(
            field_path=field_path,
            field_name=field_name,
            category=category,
            match_type=match_type,
            relevance_score=relevance_score,
            matched_text=matched_text,
            context=context,
        )

    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions for a partial query.

        Args:
            partial_query: Partial search query
            limit: Maximum number of suggestions

        Returns:
            List of suggested search terms
        """
        if not self.index or len(partial_query) < 2:
            return []

        suggestions = set()

        # Get suggestions from word mappings
        partial_lower = partial_query.lower()
        for word in self.index.word_to_fields.keys():
            if word.startswith(partial_lower):
                suggestions.add(word)
            if len(suggestions) >= limit * 2:  # Get more than needed for filtering
                break

        # Sort by relevance (frequency in this case)
        scored_suggestions = []
        for suggestion in suggestions:
            if suggestion in self.index.word_to_fields:
                field_count = len(self.index.word_to_fields[suggestion])
                scored_suggestions.append((suggestion, field_count))

        # Sort by field count (more popular terms first)
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)

        return [suggestion for suggestion, _ in scored_suggestions[:limit]]

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the search index.

        Returns:
            Dictionary with index statistics
        """
        if not self.index:
            return {"status": "no_index"}

        stats = {
            "status": "active",
            "field_count": len(self.index.field_data),
            "category_count": len(set(self.index.category_mapping.values())),
            "word_count": len(self.index.word_to_fields),
            "build_time": self.index_build_time,
            "last_updated": self.index.last_updated,
            "cache_size": len(self.search_cache),
            "cache_hit_rate": "N/A",  # Could be calculated with hit/miss counters
        }

        # Category breakdown
        category_counts = defaultdict(int)
        for category in self.index.category_mapping.values():
            category_counts[category] += 1

        stats["categories"] = dict(category_counts)

        return stats

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self.search_cache.clear()
        self.logger.debug("Search cache cleared")

    def warm_up_cache(self, common_queries: List[str]) -> None:
        """
        Warm up the search cache with common queries.

        Args:
            common_queries: List of common search queries
        """
        self.logger.info(f"Warming up search cache with {len(common_queries)} queries")

        for query in common_queries:
            try:
                self.search_with_index(query)
            except Exception as e:
                self.logger.warning(f"Failed to warm up cache for query '{query}': {e}")

        self.logger.info(f"Cache warmed up, {len(self.search_cache)} queries cached")

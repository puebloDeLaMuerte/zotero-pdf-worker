"""
Author Matching Module

This module handles matching Zotero items to authors based on the configuration.
It filters creators by type and matches them against author identifiers.
"""

import logging
from typing import List, Dict, Any, Set
from dataclasses import dataclass


@dataclass
class AuthorMatch:
    """Represents a matched item for an author."""
    item: Dict[str, Any]
    matched_creator: Dict[str, Any]
    matched_identifier: str


class AuthorMatcher:
    """Handles matching Zotero items to authors."""
    
    def __init__(self, authors_config: List[Dict[str, Any]], include_creator_types: List[str]):
        """
        Initialize the author matcher.
        
        Args:
            authors_config: List of author configurations from config.json
            include_creator_types: List of creator types to include (e.g., ['author'])
        """
        self.authors_config = authors_config
        self.include_creator_types = include_creator_types
        self.logger = logging.getLogger(__name__)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        return name.lower().strip()
    
    def _get_creator_full_name(self, creator: Dict[str, Any]) -> str:
        """Get the full name of a creator."""
        first_name = creator.get('firstName', '').strip()
        last_name = creator.get('lastName', '').strip()
        return f"{first_name} {last_name}".strip()
    
    def _matches_author_identifiers(self, creator: Dict[str, Any], author_identifiers: List[str]) -> tuple[bool, str]:
        """
        Check if a creator matches any of the author identifiers.
        
        Args:
            creator: Zotero creator object
            author_identifiers: List of identifier strings for the author
            
        Returns:
            Tuple of (matches, matched_identifier)
        """
        creator_name = self._get_creator_full_name(creator)
        normalized_creator_name = self._normalize_name(creator_name)
        
        for identifier in author_identifiers:
            normalized_identifier = self._normalize_name(identifier)
            
            # Check if identifier matches the full name
            if normalized_identifier == normalized_creator_name:
                return True, identifier
            
            # Check if identifier matches just the last name
            creator_last_name = self._normalize_name(creator.get('lastName', ''))
            if normalized_identifier == creator_last_name:
                return True, identifier
            
            # Check if identifier is contained in the full name
            if normalized_identifier in normalized_creator_name:
                return True, identifier
        
        return False, ""
    
    def _filter_creators_by_type(self, creators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter creators to only include specified types."""
        return [
            creator for creator in creators
            if creator.get('creatorType') in self.include_creator_types
        ]
    
    def match_items_to_authors(self, items: List[Dict[str, Any]]) -> Dict[str, List[AuthorMatch]]:
        """
        Match Zotero items to authors based on the configuration.
        
        Args:
            items: List of Zotero items
            
        Returns:
            Dictionary mapping author slug to list of AuthorMatch objects
        """
        author_matches = {author['slug']: [] for author in self.authors_config}
        
        self.logger.info(f"Starting author matching for {len(items)} items and {len(self.authors_config)} authors")
        
        for item in items:
            if 'data' not in item:
                continue
                
            item_data = item['data']
            creators = item_data.get('creators', [])
            
            # Filter creators by type
            relevant_creators = self._filter_creators_by_type(creators)
            
            if not relevant_creators:
                continue
            
            # Check each author configuration
            for author_config in self.authors_config:
                author_slug = author_config['slug']
                author_identifiers = author_config['identifiers']
                
                # Check if any relevant creator matches this author
                for creator in relevant_creators:
                    matches, matched_identifier = self._matches_author_identifiers(creator, author_identifiers)
                    
                    if matches:
                        author_match = AuthorMatch(
                            item=item,
                            matched_creator=creator,
                            matched_identifier=matched_identifier
                        )
                        author_matches[author_slug].append(author_match)
                        
                        self.logger.debug(f"Matched item '{item_data.get('title', 'No title')}' to author '{author_slug}' via identifier '{matched_identifier}'")
                        break  # Don't match the same item multiple times to the same author
        
        # Log summary
        for author_slug, matches in author_matches.items():
            self.logger.info(f"Author '{author_slug}': {len(matches)} matched items")
        
        return author_matches
    
    def get_author_statistics(self, author_matches: Dict[str, List[AuthorMatch]]) -> Dict[str, Any]:
        """
        Get statistics about the author matching results.
        
        Args:
            author_matches: Results from match_items_to_authors
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_authors': len(author_matches),
            'authors_with_items': sum(1 for matches in author_matches.values() if matches),
            'total_matched_items': sum(len(matches) for matches in author_matches.values()),
            'author_breakdown': {}
        }
        
        for author_slug, matches in author_matches.items():
            stats['author_breakdown'][author_slug] = {
                'item_count': len(matches),
                'item_types': {}
            }
            
            # Count item types
            for match in matches:
                item_type = match.item['data'].get('itemType', 'unknown')
                stats['author_breakdown'][author_slug]['item_types'][item_type] = \
                    stats['author_breakdown'][author_slug]['item_types'].get(item_type, 0) + 1
        
        return stats 
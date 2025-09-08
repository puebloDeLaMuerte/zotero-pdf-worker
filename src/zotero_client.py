"""
Zotero API Client

This module handles all interactions with the Zotero API:
- Fetching items from a group collection
- Getting formatted citations
- Handling API rate limits and errors
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin


class ZoteroClient:
    """Client for interacting with the Zotero API."""
    
    BASE_URL = "https://api.zotero.org"
    
    def __init__(
        self, 
        group_id: str, 
        api_key: str, 
        collection_key: Optional[str] = None,
        citation_style: str = "chicago-author-date",
        locale: str = "de-DE"
    ):
        """
        Initialize the Zotero client.
        
        Args:
            group_id: Zotero group ID
            api_key: Zotero API key
            collection_key: Optional collection key to filter items
            citation_style: Citation style for formatted citations
            locale: Locale for citations
        """
        self.group_id = group_id
        self.api_key = api_key
        self.collection_key = collection_key
        self.citation_style = citation_style
        self.locale = locale
        self.logger = logging.getLogger(__name__)
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Zotero-API-Key': self.api_key,
            'User-Agent': 'Zotero-PDF-Worker/1.0'
        })
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL for API endpoint."""
        return urljoin(self.BASE_URL, f"/groups/{self.group_id}/{endpoint}")
    
    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Make a request to the Zotero API with error handling and retry logic.
        
        Args:
            url: Full URL to request
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response data
            
        Raises:
            requests.RequestException: If the request fails after all retries
        """
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Making request to: {url} (attempt {attempt + 1})")
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # Check rate limit headers
                if 'X-Rate-Limit-Remaining' in response.headers:
                    remaining = int(response.headers['X-Rate-Limit-Remaining'])
                    if remaining < 10:
                        self.logger.warning(f"Low rate limit remaining: {remaining}")
                
                return response.json()
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise
    
    def fetch_collection_items(self) -> List[Dict[str, Any]]:
        """
        Fetch all items from the specified collection.
        
        Returns:
            List of Zotero items (without formatted citations initially)
        """
        # Build the items endpoint
        if self.collection_key:
            endpoint = f"collections/{self.collection_key}/items"
        else:
            endpoint = "items"
        
        url = self._build_url(endpoint)
        
        # Parameters for the request - NO include=bib to avoid timeouts
        params = {
            'format': 'json',
            'limit': 100  # Maximum items per request
        }
        
        all_items = []
        start = 0
        
        while True:
            # Add pagination parameters
            current_params = params.copy()
            current_params['start'] = start
            
            self.logger.info(f"Fetching items {start} to {start + params['limit'] - 1}")
            
            # Make the request
            data = self._make_request(url, current_params)
            
            # Extract items from response - handle both dict and list formats
            if isinstance(data, dict):
                items = data.get('data', [])
            elif isinstance(data, list):
                items = data
            else:
                self.logger.error(f"Unexpected response format: {type(data)}")
                break
            
            if not items:
                break
            
            all_items.extend(items)
            start += len(items)
            
            # If we got fewer items than the limit, we've reached the end
            if len(items) < params['limit']:
                break
        
        self.logger.info(f"Fetched {len(all_items)} total items")
        return all_items
    
    def get_item_citation(self, item_key: str) -> Optional[str]:
        """
        Get formatted citation for a specific item.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            Formatted citation string or None if not found
        """
        url = self._build_url(f"items/{item_key}")
        params = {
            'format': 'json',
            'include': 'bib',
            'style': self.citation_style,
            'locale': self.locale
        }
        
        try:
            data = self._make_request(url, params)
            
            # The API returns the citation directly in the 'bib' key
            if 'bib' in data:
                citation = data['bib']
                self.logger.debug(f"Got formatted citation for {item_key}")
                return citation
            else:
                self.logger.debug(f"No 'bib' key in response for {item_key}")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get citation for item {item_key}: {e}")
        
        return None
    
    def get_items_citations(self, item_keys: List[str]) -> Dict[str, str]:
        """
        Get formatted citations for multiple items in batch.
        
        Args:
            item_keys: List of Zotero item keys
            
        Returns:
            Dictionary mapping item_key to citation string
        """
        citations = {}
        
        # Process in smaller batches to avoid timeouts
        batch_size = 10
        for i in range(0, len(item_keys), batch_size):
            batch = item_keys[i:i + batch_size]
            self.logger.info(f"Getting citations for batch {i//batch_size + 1} ({len(batch)} items)")
            
            for item_key in batch:
                citation = self.get_item_citation(item_key)
                if citation:
                    citations[item_key] = citation
                
                # Small delay between requests to be nice to the API
                time.sleep(0.1)
        
        return citations
    
    def test_connection(self) -> bool:
        """
        Test the connection to Zotero API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            url = self._build_url("")
            self._make_request(url)
            self.logger.info("Zotero API connection test successful")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Zotero API connection test failed: {e}")
            return False 
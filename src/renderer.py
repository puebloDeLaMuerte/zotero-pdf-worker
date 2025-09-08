"""
HTML Preprocessor and Renderer

This module handles converting Zotero data into HTML for PDF generation.
It can work with both per-author lists and complete bibliographies.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Environment, BaseLoader, Template
from zotero_client import ZoteroClient


class HTMLPreprocessor:
    """Handles preprocessing Zotero data into HTML format."""
    
    def __init__(self, zotero_client: ZoteroClient, config: Dict[str, Any]):
        """
        Initialize the HTML preprocessor.
        
        Args:
            zotero_client: ZoteroClient instance for fetching citations
            config: Configuration dictionary
        """
        self.zotero_client = zotero_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up Jinja2 environment
        self.jinja_env = Environment(loader=BaseLoader())
    
    def _get_item_citation(self, item: Dict[str, Any]) -> str:
        """
        Get formatted citation for an item.
        
        Args:
            item: Zotero item
            
        Returns:
            Formatted citation string
        """
        item_key = item.get('key')
        if not item_key:
            self.logger.debug("No item key found, using fallback citation")
            return "No citation available"
        
        # Try to get formatted citation from Zotero API
        self.logger.info(f"Fetching citation for item {item_key}...")
        citation = self.zotero_client.get_item_citation(item_key)
        
        if citation:
            self.logger.info(f"✓ Got formatted citation for {item_key}: {citation[:50]}...")
            return citation
        else:
            self.logger.info(f"✗ No formatted citation for {item_key}, using fallback")
            fallback = self._create_fallback_citation(item)
            self.logger.info(f"Fallback citation: {fallback}")
            return fallback
    
    def _create_fallback_citation(self, item: Dict[str, Any]) -> str:
        """
        Create a basic citation when formatted citation is not available.
        
        Args:
            item: Zotero item
            
        Returns:
            Basic citation string
        """
        if 'data' not in item:
            self.logger.debug("No item data found for fallback citation")
            return "No citation available"
        
        item_data = item['data']
        title = item_data.get('title', 'No title')
        creators = item_data.get('creators', [])
        
        self.logger.debug(f"Creating fallback citation for: {title}")
        
        # Get first author
        author_names = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                first_name = creator.get('firstName', '')
                last_name = creator.get('lastName', '')
                if last_name:
                    author_names.append(f"{last_name}, {first_name}".strip(', '))
        
        if author_names:
            authors = ', '.join(author_names[:3])  # Limit to first 3 authors
            if len(author_names) > 3:
                authors += " et al."
            self.logger.debug(f"Found authors: {authors}")
        else:
            authors = "Unknown author"
            self.logger.debug("No authors found, using 'Unknown author'")
        
        fallback_citation = f"{authors}. {title}."
        self.logger.debug(f"Created fallback citation: {fallback_citation}")
        return fallback_citation
    
    def _sort_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort items alphabetically by title.
        
        Args:
            items: List of Zotero items
            
        Returns:
            Sorted list of items
        """
        self.logger.debug(f"Sorting {len(items)} items alphabetically by title")
        
        def get_sort_key(item):
            if 'data' not in item:
                return "zzz_no_title"
            return item['data'].get('title', 'zzz_no_title').lower()
        
        sorted_items = sorted(items, key=get_sort_key)
        
        # Log first few titles for debugging
        for i, item in enumerate(sorted_items[:5]):
            if 'data' in item:
                title = item['data'].get('title', 'No title')
                self.logger.debug(f"Sorted item {i+1}: {title}")
        
        if len(sorted_items) > 5:
            self.logger.debug(f"... and {len(sorted_items) - 5} more items")
        
        return sorted_items
    
    def _prepare_items_for_html(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare items for HTML rendering by adding citation data.
        
        Args:
            items: List of Zotero items
            
        Returns:
            List of items with added citation data
        """
        self.logger.info(f"Preparing {len(items)} items for HTML rendering...")
        
        prepared_items = []
        for i, item in enumerate(items):
            if 'data' not in item:
                self.logger.debug(f"Skipping item {i+1}: no data found")
                continue
            
            item_data = item['data']
            title = item_data.get('title', 'No title')
            
            self.logger.debug(f"Processing item {i+1}/{len(items)}: {title}")
            
            # Get formatted citation from Zotero API
            citation = self._get_item_citation(item)
            
            prepared_item = {
                'title': title,
                'citation': citation,
                'key': item.get('key', 'unknown'),
                'data': item_data
            }
            
            prepared_items.append(prepared_item)
        
        self.logger.info(f"Prepared {len(prepared_items)} items for HTML rendering")
        return prepared_items
    
    def create_html_template(self) -> str:
        """
        Create the HTML template for bibliography rendering.
        
        Returns:
            HTML template string
        """
        template_str = """
<!DOCTYPE html>
<html lang="{{ locale }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="layout.css">
</head>
<body>
    <h1>NETZWERK<br>HERKÜNFTE</h1>
    
    <h2>{{ subtitle }}</h2>
    
    <div class="bibliography">
        {% for item in items %}
        <div class="bibliography-item">
            <span class="citation">{{ item.citation }}</span>
        </div>
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>Generated on {{ generated_at }} | {{ total_items }} items | {{ citation_style }} style</p>
    </div>
</body>
</html>
        """
        return template_str
    
    def render_to_html(self, items: List[Dict[str, Any]], title: str, subtitle: Optional[str] = None) -> str:
        """
        Render items to HTML.
        
        Args:
            items: List of Zotero items
            title: Title for the bibliography
            subtitle: Optional subtitle
            
        Returns:
            HTML string
        """
        self.logger.info(f"Rendering {len(items)} items to HTML with title: {title}")
        
        # Prepare items for rendering
        prepared_items = self._prepare_items_for_html(items)
        
        # Get template
        template_str = self.create_html_template()
        template = self.jinja_env.from_string(template_str)
        
        # Prepare template data
        template_data = {
            'title': title,
            'subtitle': subtitle,
            'items': prepared_items,
            'total_items': len(prepared_items),
            'locale': self.config['general']['locale'],
            'citation_style': self.config['general']['citation_style'],
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Render HTML
        html = template.render(**template_data)
        
        self.logger.info(f"HTML rendering complete: {len(html)} characters")
        return html
    
    def render_per_author_bibliography(self, author_slug: str, items: List[Dict[str, Any]]) -> str:
        """
        Render a per-author bibliography.
        
        Args:
            author_slug: Author slug for the bibliography
            items: List of items for this author
            
        Returns:
            HTML string
        """
        # Convert slug to readable title
        title = author_slug.replace('-', ' ').title()
        subtitle = f"Bibliography of {title}"
        
        return self.render_to_html(items, title, subtitle)
    
    def render_complete_bibliography(self, items: List[Dict[str, Any]]) -> str:
        """
        Render a complete bibliography.
        
        Args:
            items: List of all items
            
        Returns:
            HTML string
        """
        title = "Netzwerk Herkünfte"
        subtitle = f"Complete Bibliography - All {len(items)} items from the collection"
        
        return self.render_to_html(items, title, subtitle) 
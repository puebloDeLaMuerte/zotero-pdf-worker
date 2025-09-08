#!/usr/bin/env python3
"""
Zotero PDF Worker - Main orchestration entrypoint

This module coordinates the entire workflow:
1. Load configuration from .env and config.json
2. Fetch data from Zotero API
3. Process authors and their works
4. Generate bibliography PDFs
5. Write to WordPress uploads directory
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from zotero_client import ZoteroClient
from authors import AuthorMatcher
from renderer import HTMLPreprocessor


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json and environment variables."""
    config_path = Path(__file__).parent.parent / "config.json"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Load environment variables
    env_vars = {
        'wp_uploads_path': os.getenv('WP_UPLOADS_PATH'),
        'site_id': os.getenv('SITE_ID'),
        'bib_root': os.getenv('BIB_ROOT'),
        'permalink_dir': os.getenv('PERMALINK_DIR'),
        'history_dir': os.getenv('HISTORY_DIR'),
        'zotero_api_key': os.getenv('ZOTERO_API_KEY'),
    }
    
    # Validate required environment variables
    missing_vars = [key for key, value in env_vars.items() if value is None]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    config['env'] = env_vars
    return config


def setup_logging(config: Dict[str, Any]) -> None:
    """Set up logging configuration."""
    log_file = config['general'].get('log_file', './generate.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def fetch_zotero_data(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch all data from Zotero API.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of Zotero items
    """
    logger = logging.getLogger(__name__)
    
    # Initialize Zotero client
    zotero_config = config['zotero']
    zotero_client = ZoteroClient(
        group_id=zotero_config['group_id'],
        api_key=config['env']['zotero_api_key'],
        collection_key=zotero_config.get('collection_key'),
        citation_style=config['general']['citation_style'],
        locale=config['general']['locale']
    )
    
    # Test connection first
    if not zotero_client.test_connection():
        raise ConnectionError("Failed to connect to Zotero API")
    
    # Fetch data from Zotero
    logger.info("Fetching items from Zotero...")
    items = zotero_client.fetch_collection_items()
    logger.info(f"Retrieved {len(items)} items from Zotero")
    
    return items


def create_per_author_lists(items: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create per-author lists of items.
    
    Args:
        items: List of Zotero items
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping author slug to list of items
    """
    logger = logging.getLogger(__name__)
    
    # Initialize author matcher
    author_matcher = AuthorMatcher(
        authors_config=config['authors'],
        include_creator_types=config['general']['include_creator_types']
    )
    
    # Match items to authors
    logger.info("Matching items to authors...")
    author_matches = author_matcher.match_items_to_authors(items)
    
    # Convert AuthorMatch objects to simple item lists
    per_author_lists = {}
    for author_slug, matches in author_matches.items():
        per_author_lists[author_slug] = [match.item for match in matches]
    
    # Get and log statistics
    stats = author_matcher.get_author_statistics(author_matches)
    logger.info(f"Author matching complete:")
    logger.info(f"  - Total authors: {stats['total_authors']}")
    logger.info(f"  - Authors with items: {stats['authors_with_items']}")
    logger.info(f"  - Total matched items: {stats['total_matched_items']}")
    
    return per_author_lists


def create_complete_bibliography(items: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a complete bibliography from all items.
    
    Args:
        items: List of all Zotero items
        config: Configuration dictionary
        
    Returns:
        Dictionary containing complete bibliography data
    """
    logger = logging.getLogger(__name__)
    
    logger.info("Creating complete bibliography...")
    
    # Filter items by type if specified
    item_types = config['general'].get('item_types', 'all')
    if item_types != 'all':
        # TODO: Implement item type filtering
        pass
    
    # Create complete bibliography structure
    complete_bib = {
        'title': 'Complete Bibliography',
        'total_items': len(items),
        'items': items,
        'metadata': {
            'generated_at': None,  # Will be set by renderer
            'citation_style': config['general']['citation_style'],
            'locale': config['general']['locale']
        }
    }
    
    logger.info(f"Complete bibliography created with {len(items)} items")
    
    return complete_bib


def main():
    """Main orchestration function."""
    try:
        # Load configuration
        config = load_config()
        
        # Set up logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Zotero PDF Worker")
        
        # Step 1: Fetch all data from Zotero
        items = fetch_zotero_data(config)
        
        # Step 2: Create per-author lists
        #per_author_lists = create_per_author_lists(items, config)
        
        # Step 3: Create complete bibliography
        complete_bib = create_complete_bibliography(items, config)
        
        # Step 4: Initialize Zotero client for HTML preprocessor
        zotero_config = config['zotero']
        zotero_client = ZoteroClient(
            group_id=zotero_config['group_id'],
            api_key=config['env']['zotero_api_key'],
            collection_key=zotero_config.get('collection_key'),
            citation_style=config['general']['citation_style'],
            locale=config['general']['locale']
        )
        
        # Step 5: Initialize HTML preprocessor
        logger.info("Initializing HTML preprocessor...")
        html_preprocessor = HTMLPreprocessor(zotero_client, config)
        logger.info("HTML preprocessor initialized successfully")
        
        # Step 6: Generate HTML for complete bibliography
        logger.info("Generating HTML for complete bibliography...")
        logger.info(f"Processing {len(complete_bib['items'])} items from complete bibliography")
        
        html_content = html_preprocessor.render_complete_bibliography(complete_bib['items'])
        
        # Step 7: Save HTML to file for testing
        logger.info("Saving HTML to file...")
        html_file = Path(config['env']['wp_uploads_path']) / "test_bibliography.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"HTML file path: {html_file}")
        logger.debug(f"HTML file directory exists: {html_file.parent.exists()}")
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML saved successfully to: {html_file}")
        logger.info(f"HTML file size: {len(html_content)} characters")
        
        # Step 8: Create PDF from HTML
        logger.info("Creating PDF from HTML...")
        from pdf_creator import PDFCreator
        
        pdf_creator = PDFCreator(config)
        pdf_file = Path(config['env']['wp_uploads_path']) / "test_bibliography.pdf"
        
        success = pdf_creator.create_pdf_from_html(html_content, pdf_file)
        
        if success:
            logger.info(f"PDF created successfully: {pdf_file}")
        else:
            logger.error("Failed to create PDF")
        
        logger.info("Zotero PDF Worker completed successfully")
        
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main() 
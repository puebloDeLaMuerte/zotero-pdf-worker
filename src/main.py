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
from typing import Dict, Any

from zotero_client import ZoteroClient


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


def main():
    """Main orchestration function."""
    try:
        # Load configuration
        config = load_config()
        
        # Set up logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Zotero PDF Worker")
        
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
            logger.error("Failed to connect to Zotero API")
            return
        
        # Fetch data from Zotero
        logger.info("Fetching data from Zotero...")
        items = zotero_client.fetch_collection_items()
        logger.info(f"Retrieved {len(items)} items from Zotero")
        
        # Debug: Show structure of fetched data
        if items:
            logger.info("=== DEBUG: Sample item structure ===")
            sample_item = items[0]
            logger.info(f"Sample item keys: {list(sample_item.keys())}")
            
            # The actual item data is nested in the 'data' key
            if 'data' in sample_item:
                item_data = sample_item['data']
                logger.info(f"Item data keys: {list(item_data.keys())}")
                logger.info(f"Sample item type: {item_data.get('itemType', 'unknown')}")
                logger.info(f"Sample item title: {item_data.get('title', 'no title')}")
                logger.info(f"Sample item creators: {item_data.get('creators', [])}")
            else:
                logger.info("No 'data' key found in item")
            logger.info("=== END DEBUG ===")
            
            # Show a few more items for variety
            logger.info("=== DEBUG: First 3 items summary ===")
            for i, item in enumerate(items[:3]):
                if 'data' in item:
                    item_data = item['data']
                    title = item_data.get('title', 'No title')
                    item_type = item_data.get('itemType', 'unknown')
                    creators = item_data.get('creators', [])
                    creator_names = [c.get('lastName', '') + ', ' + c.get('firstName', '') for c in creators if c.get('creatorType') == 'author']
                    logger.info(f"Item {i+1}: {title} ({item_type}) - Authors: {creator_names}")
                else:
                    logger.info(f"Item {i+1}: No data found")
            logger.info("=== END DEBUG ===")
        else:
            logger.warning("No items retrieved from Zotero")
        
        # TODO: Process authors and generate PDFs
        # This will be implemented in subsequent modules
        
        logger.info("Zotero PDF Worker completed successfully")
        
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main() 
"""
PDF Creator Module

This module handles converting HTML to PDF using WeasyPrint.
It includes proper font handling and pagination.
"""

import logging
from pathlib import Path
from typing import Optional
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


class PDFCreator:
    """Handles PDF generation from HTML."""
    
    def __init__(self, config: dict):
        """
        Initialize the PDF creator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up font configuration
        self.font_config = FontConfiguration()
        
        # Get CSS file path
        self.css_file = self._get_css_file_path()
    
    def _get_css_file_path(self) -> Path:
        """Get the path to the CSS file."""
        css_file = Path(__file__).parent / "layout.css"
        if not css_file.exists():
            raise FileNotFoundError(f"CSS file not found: {css_file}")
        return css_file
    
    def create_pdf_from_html(self, html_content: str, output_path: Path) -> bool:
        """
        Create a PDF from HTML content.
        
        Args:
            html_content: HTML content as string
            output_path: Path where to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating PDF from HTML content...")
            self.logger.info(f"Output path: {output_path}")
            self.logger.info(f"CSS file: {self.css_file}")
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create HTML object
            html_doc = HTML(string=html_content)
            
            # Create CSS object
            css_doc = CSS(filename=str(self.css_file), font_config=self.font_config)
            
            # Generate PDF
            self.logger.info("Generating PDF with WeasyPrint...")
            html_doc.write_pdf(
                str(output_path),
                stylesheets=[css_doc],
                font_config=self.font_config
            )
            
            # Check if file was created
            if output_path.exists():
                file_size = output_path.stat().st_size
                self.logger.info(f"PDF created successfully: {output_path}")
                self.logger.info(f"File size: {file_size:,} bytes")
                return True
            else:
                self.logger.error("PDF file was not created")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating PDF: {e}", exc_info=True)
            return False
    
    def create_pdf_from_file(self, html_file_path: Path, output_path: Path) -> bool:
        """
        Create a PDF from an HTML file.
        
        Args:
            html_file_path: Path to the HTML file
            output_path: Path where to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not html_file_path.exists():
                self.logger.error(f"HTML file not found: {html_file_path}")
                return False
            
            self.logger.info(f"Creating PDF from HTML file: {html_file_path}")
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create HTML object from file
            html_doc = HTML(filename=str(html_file_path))
            
            # Create CSS object
            css_doc = CSS(filename=str(self.css_file), font_config=self.font_config)
            
            # Generate PDF
            self.logger.info("Generating PDF with WeasyPrint...")
            html_doc.write_pdf(
                str(output_path),
                stylesheets=[css_doc],
                font_config=self.font_config
            )
            
            # Check if file was created
            if output_path.exists():
                file_size = output_path.stat().st_size
                self.logger.info(f"PDF created successfully: {output_path}")
                self.logger.info(f"File size: {file_size:,} bytes")
                return True
            else:
                self.logger.error("PDF file was not created")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating PDF: {e}", exc_info=True)
            return False

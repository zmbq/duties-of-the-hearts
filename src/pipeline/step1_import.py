"""
Step 1: Import JSON book data into the database.

This script reads the Duties of the Heart JSON file and populates the database
with chapters, sections, and paragraphs using Hebrew titles from the schema.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from src.models import init_db, Chapter, Section, Paragraph
from src.utils import config


def clean_html_tags(text: str) -> str:
    """
    Remove HTML tags from text while preserving the content.
    
    Args:
        text: Text that may contain HTML tags
        
    Returns:
        Clean text without HTML tags
    """
    # Remove HTML tags using regex
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text.strip()


def load_json_book(json_path: Path) -> Dict[str, Any]:
    """Load the book JSON file."""
    print(f"Loading book from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_hebrew_titles(schema_nodes: List[Dict]) -> Dict[str, str]:
    """
    Extract Hebrew titles from schema nodes.
    Returns a dict mapping English titles to Hebrew titles.
    """
    title_map = {}
    
    for node in schema_nodes:
        en_title = node.get('enTitle', '')
        he_title = node.get('heTitle', '')
        
        # Store main chapter title
        if en_title and he_title:
            title_map[en_title] = he_title
        
        # Process section nodes if they exist
        if 'nodes' in node:
            for section_node in node['nodes']:
                section_en = section_node.get('enTitle', '')
                section_he = section_node.get('heTitle', '')
                if section_en and section_he:
                    # Create a composite key for sections: "ChapterTitle|SectionTitle"
                    title_map[f"{en_title}|{section_en}"] = section_he
    
    return title_map


def import_book(session: Session, book_data: Dict[str, Any]) -> None:
    """
    Import book data into the database.
    
    Args:
        session: SQLAlchemy session
        book_data: Parsed JSON data from the book file
    """
    # Get Hebrew titles from schema
    schema = book_data.get('schema', {})
    nodes = schema.get('nodes', [])
    hebrew_titles = get_hebrew_titles(nodes)
    
    print(f"Found {len(hebrew_titles)} Hebrew titles in schema")
    
    # Get the text content
    text_data = book_data.get('text', {})
    
    chapter_number = 0
    total_paragraphs = 0
    
    # Process each chapter
    for english_title, content in text_data.items():
        chapter_number += 1
        
        # Get Hebrew title for this chapter
        hebrew_title = hebrew_titles.get(english_title, english_title)
        
        print(f"\nProcessing Chapter {chapter_number}: {hebrew_title} ({english_title})")
        
        # Create chapter
        chapter = Chapter(
            title=hebrew_title,
            chapter_number=chapter_number
        )
        session.add(chapter)
        session.flush()  # Get the chapter ID
        
        # Check if content is a dictionary (has sections) or a list (no sections)
        if isinstance(content, dict):
            # Content has sections
            print(f"  Chapter has {len(content)} sections")
            
            section_number = 0
            for section_english_title, section_content in content.items():
                section_number += 1
                
                # Get Hebrew title for this section
                # Empty string means unnamed section
                if section_english_title:
                    section_key = f"{english_title}|{section_english_title}"
                    section_hebrew_title = hebrew_titles.get(section_key, section_english_title)
                else:
                    # Empty section title - use a numbered title
                    section_hebrew_title = f"פרק {section_number}"
                
                # Create section
                section = Section(
                    chapter_id=chapter.id,
                    title=section_hebrew_title,
                    section_number=section_number
                )
                session.add(section)
                session.flush()
                
                # Add paragraphs to this section
                # Section content might be a list of paragraphs or a list of lists (subsections)
                if section_content and len(section_content) > 0 and isinstance(section_content[0], list):
                    # Nested structure - flatten it
                    paragraph_number = 0
                    for subsection in section_content:
                        for paragraph_text in subsection:
                            clean_text = clean_html_tags(paragraph_text)
                            if clean_text:  # Skip empty paragraphs
                                paragraph_number += 1
                                paragraph = Paragraph(
                                    chapter_id=chapter.id,
                                    section_id=section.id,
                                    paragraph_number=paragraph_number,
                                    text=clean_text
                                )
                                session.add(paragraph)
                                total_paragraphs += 1
                    para_count = paragraph_number
                else:
                    # Flat list of paragraphs
                    para_count = 0
                    for paragraph_number, paragraph_text in enumerate(section_content, start=1):
                        clean_text = clean_html_tags(paragraph_text)
                        if clean_text:  # Skip empty paragraphs
                            paragraph = Paragraph(
                                chapter_id=chapter.id,
                                section_id=section.id,
                                paragraph_number=paragraph_number,
                                text=clean_text
                            )
                            session.add(paragraph)
                            total_paragraphs += 1
                            para_count += 1
                
                print(f"    Section {section_number} ({section_hebrew_title}): {para_count} paragraphs")
        
        else:
            # Content is a flat list of paragraphs (no sections)
            print(f"  Chapter has {len(content)} paragraphs (no sections)")
            
            for paragraph_number, paragraph_text in enumerate(content, start=1):
                clean_text = clean_html_tags(paragraph_text)
                if clean_text:  # Skip empty paragraphs
                    paragraph = Paragraph(
                        chapter_id=chapter.id,
                        section_id=None,  # No section
                        paragraph_number=paragraph_number,
                        text=clean_text
                    )
                    session.add(paragraph)
                    total_paragraphs += 1
    
    # Commit all changes
    session.commit()
    print(f"\n{'='*60}")
    print(f"Import completed successfully!")
    print(f"Imported {chapter_number} chapters with {total_paragraphs} total paragraphs")
    print(f"{'='*60}")


def main():
    """Main function to run the import process."""
    # Initialize database
    print("Initializing database...")
    engine, SessionLocal = init_db(config.database_url)
    
    # Get the JSON file path
    json_file = config.assets_dir / "Duties of the Heart - he - Vocalized Edition (1).json"
    
    if not json_file.exists():
        print(f"Error: Book file not found at {json_file}")
        return
    
    # Load book data
    book_data = load_json_book(json_file)
    
    # Import into database
    session = SessionLocal()
    try:
        import_book(session, book_data)
    except Exception as e:
        print(f"Error during import: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    print("\nDatabase import complete!")


if __name__ == "__main__":
    main()

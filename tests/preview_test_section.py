"""
Preview the section we're about to translate.
"""

from src.models import init_db, Chapter, Section, Paragraph
from src.utils import config


def main():
    """Show the test section content."""
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Chapter 6, Section 1
        chapter = session.query(Chapter).filter(Chapter.chapter_number == 6).first()
        section = session.query(Section).filter(
            Section.chapter_id == chapter.id,
            Section.section_number == 1
        ).first()
        
        paragraphs = session.query(Paragraph).filter(
            Paragraph.section_id == section.id
        ).order_by(Paragraph.paragraph_number).all()
        
        print("=" * 80)
        print(f"PREVIEW: Test Section for Translation")
        print("=" * 80)
        print(f"Chapter: {chapter.title}")
        print(f"Section: {section.title}")
        print(f"Paragraphs: {len(paragraphs)}")
        print("=" * 80)
        
        for para in paragraphs:
            print(f"\n[{para.paragraph_number}]")
            print(para.text)
        
        print("\n" + "=" * 80)
        print(f"Ready to translate {len(paragraphs)} paragraphs")
        print("Estimated cost: $0.02-0.05 (very small)")
        print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

"""
Verification script to show what was imported into the database.
"""

from sqlalchemy import func
from src.models import init_db, Chapter, Section, Paragraph
from src.utils import config


def main():
    """Verify the database import."""
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get counts
        chapter_count = session.query(func.count(Chapter.id)).scalar()
        section_count = session.query(func.count(Section.id)).scalar()
        paragraph_count = session.query(func.count(Paragraph.id)).scalar()
        
        print("=" * 60)
        print("Database Import Verification")
        print("=" * 60)
        print(f"Total Chapters: {chapter_count}")
        print(f"Total Sections: {section_count}")
        print(f"Total Paragraphs: {paragraph_count}")
        print()
        
        # Show all chapters
        print("Chapters:")
        print("-" * 60)
        chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()
        for chapter in chapters:
            para_count = session.query(func.count(Paragraph.id)).filter(
                Paragraph.chapter_id == chapter.id
            ).scalar()
            section_count_ch = session.query(func.count(Section.id)).filter(
                Section.chapter_id == chapter.id
            ).scalar()
            
            print(f"{chapter.chapter_number}. {chapter.title}")
            print(f"   Sections: {section_count_ch}, Paragraphs: {para_count}")
            
            # Show sections for this chapter
            sections = session.query(Section).filter(
                Section.chapter_id == chapter.id
            ).order_by(Section.section_number).all()
            
            for section in sections:
                section_para_count = session.query(func.count(Paragraph.id)).filter(
                    Paragraph.section_id == section.id
                ).scalar()
                print(f"     {section.section_number}. {section.title} ({section_para_count} paragraphs)")
        
        print()
        print("=" * 60)
        print("Sample paragraph (first paragraph):")
        print("-" * 60)
        first_para = session.query(Paragraph).first()
        if first_para:
            print(f"Chapter: {first_para.chapter.title}")
            print(f"Paragraph {first_para.paragraph_number}:")
            print(first_para.text[:200] + "..." if len(first_para.text) > 200 else first_para.text)
        
        print()
        print("=" * 60)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

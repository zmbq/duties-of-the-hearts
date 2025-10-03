"""
Analyze section lengths to help plan translation strategy.
"""

from sqlalchemy import func
from src.models import init_db, Chapter, Section, Paragraph
from src.utils import config


def main():
    """Analyze section lengths in the database."""
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        print("=" * 80)
        print("Section Length Analysis")
        print("=" * 80)
        
        # Get all chapters
        chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()
        
        total_sections = 0
        sections_by_size = {
            'tiny': [],      # 1-10 paragraphs
            'small': [],     # 11-30 paragraphs
            'medium': [],    # 31-60 paragraphs
            'large': [],     # 61-100 paragraphs
            'huge': []       # 100+ paragraphs
        }
        
        for chapter in chapters:
            print(f"\n{chapter.chapter_number}. {chapter.title}")
            print("-" * 80)
            
            # Get sections for this chapter
            sections = session.query(Section).filter(
                Section.chapter_id == chapter.id
            ).order_by(Section.section_number).all()
            
            if sections:
                for section in sections:
                    para_count = session.query(func.count(Paragraph.id)).filter(
                        Paragraph.section_id == section.id
                    ).scalar()
                    
                    # Estimate tokens (rough: Hebrew word ~= 2 tokens, avg 10 words per paragraph)
                    estimated_tokens = para_count * 20
                    
                    print(f"  Section {section.section_number}: {section.title}")
                    print(f"    Paragraphs: {para_count}")
                    print(f"    Estimated input tokens: ~{estimated_tokens:,}")
                    
                    # Categorize by size
                    if para_count <= 10:
                        sections_by_size['tiny'].append((chapter.title, section.title, para_count))
                    elif para_count <= 30:
                        sections_by_size['small'].append((chapter.title, section.title, para_count))
                    elif para_count <= 60:
                        sections_by_size['medium'].append((chapter.title, section.title, para_count))
                    elif para_count <= 100:
                        sections_by_size['large'].append((chapter.title, section.title, para_count))
                    else:
                        sections_by_size['huge'].append((chapter.title, section.title, para_count))
                    
                    total_sections += 1
            else:
                # Chapter without sections
                para_count = session.query(func.count(Paragraph.id)).filter(
                    Paragraph.chapter_id == chapter.id,
                    Paragraph.section_id == None
                ).scalar()
                estimated_tokens = para_count * 20
                print(f"  No sections - {para_count} paragraphs directly")
                print(f"  Estimated input tokens: ~{estimated_tokens:,}")
        
        # Summary
        print("\n" + "=" * 80)
        print("Summary by Section Size")
        print("=" * 80)
        
        print(f"\nTiny sections (1-10 paragraphs): {len(sections_by_size['tiny'])}")
        for ch, sec, count in sections_by_size['tiny'][:5]:  # Show first 5
            print(f"  • {ch} → {sec}: {count} paragraphs")
        if len(sections_by_size['tiny']) > 5:
            print(f"  ... and {len(sections_by_size['tiny']) - 5} more")
        
        print(f"\nSmall sections (11-30 paragraphs): {len(sections_by_size['small'])}")
        for ch, sec, count in sections_by_size['small']:
            print(f"  • {ch} → {sec}: {count} paragraphs")
        
        print(f"\nMedium sections (31-60 paragraphs): {len(sections_by_size['medium'])}")
        for ch, sec, count in sections_by_size['medium']:
            print(f"  • {ch} → {sec}: {count} paragraphs")
        
        print(f"\nLarge sections (61-100 paragraphs): {len(sections_by_size['large'])}")
        for ch, sec, count in sections_by_size['large']:
            print(f"  • {ch} → {sec}: {count} paragraphs")
        
        print(f"\nHuge sections (100+ paragraphs): {len(sections_by_size['huge'])}")
        for ch, sec, count in sections_by_size['huge']:
            print(f"  • {ch} → {sec}: {count} paragraphs (~{count * 20:,} tokens)")
        
        print("\n" + "=" * 80)
        print("Recommendations:")
        print("=" * 80)
        print(f"• Total sections with text: {total_sections}")
        print(f"• Sections under 50 paragraphs: {len(sections_by_size['tiny']) + len(sections_by_size['small']) + len(sections_by_size['medium'])}")
        print(f"• Sections over 100 paragraphs: {len(sections_by_size['huge'])}")
        print("\nStrategy:")
        print("  - Small/Medium sections (≤60): Translate as single unit")
        print("  - Large sections (61-100): Translate as single unit or split in half")
        print("  - Huge sections (100+): Split into chunks of ~50 paragraphs each")
        print("\nFor testing, start with a TINY section (e.g., first section with 8-13 paragraphs)")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

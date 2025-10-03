"""
Verify and review translations in the database.
"""

from sqlalchemy import func
from src.models import init_db, Chapter, Section, Paragraph, Translation
from src.utils import config


def main():
    """Review translations."""
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get translation statistics
        total_translations = session.query(func.count(Translation.id)).scalar()
        total_paragraphs = session.query(func.count(Paragraph.id)).scalar()
        
        print("=" * 80)
        print("Translation Status")
        print("=" * 80)
        print(f"Total paragraphs: {total_paragraphs}")
        print(f"Translated paragraphs: {total_translations}")
        print(f"Remaining: {total_paragraphs - total_translations}")
        
        if total_translations == 0:
            print("\nNo translations found yet. Run step2_translate.py first.")
            return
        
        # Get translations by prompt
        print("\nTranslations by prompt:")
        print("-" * 80)
        
        prompts = session.query(Translation.prompt_name).distinct().all()
        for (prompt_name,) in prompts:
            count = session.query(func.count(Translation.id)).filter(
                Translation.prompt_name == prompt_name
            ).scalar()
            print(f"  {prompt_name}: {count} paragraphs")
        
        # Show sample translations
        print("\n" + "=" * 80)
        print("Sample Translations")
        print("=" * 80)
        
        translations = session.query(Translation).limit(5).all()
        
        for i, trans in enumerate(translations, 1):
            para = trans.paragraph
            chapter = para.chapter
            section = para.section
            
            print(f"\n[{i}] Chapter: {chapter.title}")
            if section:
                print(f"    Section: {section.title}")
            print(f"    Paragraph {para.paragraph_number}")
            print(f"    Prompt: {trans.prompt_name}")
            print(f"    Model: {trans.model}")
            print()
            print("    Original (Medieval Hebrew):")
            print(f"    {para.text[:200]}...")
            print()
            print("    Translation (Modern Hebrew):")
            print(f"    {trans.translated_text[:200]}...")
            print("    " + "-" * 76)
        
        # Detailed view of first translation
        if total_translations > 0:
            print("\n" + "=" * 80)
            print("Full Example - First Translation")
            print("=" * 80)
            
            first = session.query(Translation).first()
            para = first.paragraph
            
            print(f"\nChapter: {para.chapter.title}")
            if para.section:
                print(f"Section: {para.section.title}")
            print(f"Paragraph: {para.paragraph_number}\n")
            
            print("ORIGINAL (Medieval Hebrew):")
            print("-" * 80)
            print(para.text)
            print()
            print("TRANSLATION (Modern Hebrew):")
            print("-" * 80)
            print(first.translated_text)
            print()
            print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

"""
Test script to verify HTML tags have been removed from paragraphs.
"""

from src.models import init_db, Paragraph
from src.utils import config


def main():
    """Check for HTML tags in the database."""
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get first 10 paragraphs
        paragraphs = session.query(Paragraph).limit(10).all()
        
        print("=" * 60)
        print("Testing for HTML tags in paragraphs")
        print("=" * 60)
        
        html_tags_found = 0
        
        for para in paragraphs:
            if '<' in para.text or '>' in para.text:
                html_tags_found += 1
                print(f"\n⚠️  HTML tag found in paragraph {para.id}:")
                print(f"   {para.text[:100]}...")
        
        if html_tags_found == 0:
            print("\n✅ SUCCESS! No HTML tags found in the first 10 paragraphs.")
            print("\nSample clean paragraphs:")
            print("-" * 60)
            for i, para in enumerate(paragraphs[:3], 1):
                print(f"\n{i}. Paragraph {para.paragraph_number} from {para.chapter.title}:")
                text = para.text[:150] if len(para.text) > 150 else para.text
                print(f"   {text}...")
        else:
            print(f"\n❌ Found {html_tags_found} paragraphs with HTML tags in first 10.")
        
        print("\n" + "=" * 60)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

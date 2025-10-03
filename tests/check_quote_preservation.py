"""
Check if biblical quotes were preserved in translation.
"""

from src.models import init_db, Translation
from src.utils import config


def main():
    """Check quote preservation."""
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get the first translation (has a biblical quote)
        trans = session.query(Translation).first()
        para = trans.paragraph
        
        print("=" * 80)
        print("Quote Preservation Check")
        print("=" * 80)
        
        # The biblical quote from Job
        quote = "אל נא אשא פני איש ואל אדם לא אכנה כי לא ידעתי אכנה"
        
        print("\nOriginal text contains this biblical quote from Job (איוב לב):")
        print(f"  '{quote}'")
        
        print("\nChecking if it appears in the translation...")
        
        if quote in trans.translated_text:
            print("  ✓ YES! The biblical quote was preserved exactly!")
        else:
            # Check if it was modified
            if "אל נא" in trans.translated_text or "אשא פני" in trans.translated_text:
                print("  ⚠️  Partial match - quote might have been slightly modified")
                # Show what we got
                start = trans.translated_text.find("אל נא")
                if start > 0:
                    snippet = trans.translated_text[start:start+100]
                    print(f"     Found: '{snippet}...'")
            else:
                print("  ✗ NO - The quote was translated or modified")
        
        print("\n" + "=" * 80)
        print("Full paragraph translation:")
        print("=" * 80)
        print(trans.translated_text)
        print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

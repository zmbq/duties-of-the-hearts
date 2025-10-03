"""
Batch translation script - translate sections with customizable model and prompt.

This allows translating the same content with different models/prompts
and keeping all versions in the database for comparison.
"""

import argparse
from sqlalchemy import func

from src.models import init_db, Chapter, Section, Paragraph, Translation
from src.utils import config
from src.pipeline.step2_translate import TranslationService, translate_section_to_db


def main():
    """Main function with command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Translate sections with specified model and prompt'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default='modern',
        help='Prompt name from config.yaml (default: modern)'
    )
    parser.add_argument(
        '--chapter',
        type=int,
        help='Chapter number to translate (default: 6 for testing)'
    )
    parser.add_argument(
        '--section',
        type=int,
        help='Section number to translate (default: 1 for testing)'
    )
    parser.add_argument(
        '--model-suffix',
        type=str,
        help='Suffix to add to prompt name (e.g., "gpt4o-mini" -> prompt becomes "modern-gpt4o-mini")'
    )
    
    args = parser.parse_args()
    
    # Determine the prompt name to use
    if args.model_suffix:
        prompt_name = f"{args.prompt}-{args.model_suffix}"
        print(f"Using prompt name with suffix: {prompt_name}")
    else:
        prompt_name = args.prompt
    
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get the model being used
        current_model = config.openai_model
        print(f"Using OpenAI model: {current_model}")
        print(f"Translation will be saved as prompt: '{prompt_name}'")
        
        # Initialize translation service
        service = TranslationService(prompt_name=args.prompt)
        # Override the prompt_name for storage (to include model suffix)
        service.prompt_name = prompt_name
        
        # Find the section to translate
        chapter_num = args.chapter or 6
        section_num = args.section or 1
        
        chapter = session.query(Chapter).filter(
            Chapter.chapter_number == chapter_num
        ).first()
        
        if not chapter:
            print(f"Error: Could not find chapter {chapter_num}")
            return
        
        section = session.query(Section).filter(
            Section.chapter_id == chapter.id,
            Section.section_number == section_num
        ).first()
        
        if not section:
            print(f"Error: Could not find section {section_num} in chapter {chapter_num}")
            return
        
        # Check if already translated with this prompt
        existing_count = session.query(func.count(Translation.id)).join(
            Paragraph
        ).filter(
            Paragraph.section_id == section.id,
            Translation.prompt_name == prompt_name
        ).scalar()
        
        if existing_count > 0:
            print(f"\n⚠️  Warning: Found {existing_count} existing translations with prompt '{prompt_name}'")
            response = input("Do you want to re-translate and overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        
        print(f"\nTranslating: {chapter.title} → {section.title}")
        print(f"Model: {current_model}")
        print(f"Prompt: {prompt_name}")
        
        # Translate
        stats = translate_section_to_db(
            session=session,
            service=service,
            section=section,
            dry_run=False
        )
        
        print(f"\n{'='*80}")
        print("Translation Summary")
        print(f"{'='*80}")
        print(f"Model: {current_model}")
        print(f"Prompt: {prompt_name}")
        print(f"Translated: {stats['translated']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['translated'] > 0:
            print(f"\n✓ Successfully translated {stats['translated']} paragraphs!")
            print(f"  Saved as prompt: '{prompt_name}'")
            print(f"\nTo export this translation:")
            print(f"  python -m src.pipeline.step3_export --prompt {prompt_name}")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

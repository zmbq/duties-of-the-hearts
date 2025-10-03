"""
Translate an entire chapter with all its sections.

This script handles:
- Chapters with sections (translates each section)
- Chapters without sections (translates all paragraphs)
- Large sections (breaks into chunks of max_chunk_size paragraphs)
"""

import argparse
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import init_db, Chapter, Section, Paragraph, Translation
from src.utils import config
from src.pipeline.step2_translate import TranslationService


def chunk_paragraphs(paragraphs: List[Paragraph], max_chunk_size: int = 50) -> List[List[Paragraph]]:
    """
    Break paragraphs into chunks for large sections.
    
    Args:
        paragraphs: List of paragraphs to chunk
        max_chunk_size: Maximum paragraphs per chunk (default: 50)
        
    Returns:
        List of paragraph chunks
    """
    chunks = []
    for i in range(0, len(paragraphs), max_chunk_size):
        chunks.append(paragraphs[i:i + max_chunk_size])
    return chunks


def translate_paragraphs(
    session: Session,
    service: TranslationService,
    paragraphs: List[Paragraph],
    prompt_name: str,
    max_chunk_size: int = 50
) -> dict:
    """
    Translate a list of paragraphs, chunking if necessary.
    
    Args:
        session: Database session
        service: TranslationService instance
        paragraphs: List of paragraphs to translate
        prompt_name: Name to save translations under
        max_chunk_size: Maximum paragraphs per chunk
        
    Returns:
        Dictionary with success count and errors
    """
    total_paragraphs = len(paragraphs)
    translated_count = 0
    error_count = 0
    
    # Check if we need to chunk
    if total_paragraphs > max_chunk_size:
        chunks = chunk_paragraphs(paragraphs, max_chunk_size)
        print(f"  Large section detected: {total_paragraphs} paragraphs")
        print(f"  Breaking into {len(chunks)} chunks of ~{max_chunk_size} paragraphs each")
    else:
        chunks = [paragraphs]
    
    # Translate each chunk
    for chunk_idx, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f"\n  📦 Chunk {chunk_idx}/{len(chunks)}: {len(chunk)} paragraphs")
        
        try:
            # Check for existing translations
            existing_count = session.query(func.count(Translation.id)).join(Paragraph).filter(
                Paragraph.id.in_([p.id for p in chunk]),
                Translation.prompt_name == prompt_name
            ).scalar()
            
            if existing_count > 0:
                print(f"    ⚠️  {existing_count} paragraphs already translated")
                response = input(f"    Re-translate and overwrite? (y/N): ").strip().lower()
                if response != 'y':
                    print(f"    Skipping chunk {chunk_idx}")
                    continue
            
            # Translate the chunk
            print(f"    Calling OpenAI API...")
            translations = service.translate_section(chunk)
            
            # Save to database
            for para, trans_text in zip(chunk, translations):
                # Check if translation already exists
                existing = session.query(Translation).filter(
                    Translation.paragraph_id == para.id,
                    Translation.prompt_name == prompt_name
                ).first()
                
                if existing:
                    # Update existing
                    existing.translated_text = trans_text
                    existing.model = service.model
                else:
                    # Create new
                    translation = Translation(
                        paragraph_id=para.id,
                        prompt_name=prompt_name,
                        translated_text=trans_text,
                        model=service.model
                    )
                    session.add(translation)
            
            session.commit()
            translated_count += len(chunk)
            print(f"    ✓ Saved {len(chunk)} translations")
            
        except Exception as e:
            print(f"    ✗ Error in chunk {chunk_idx}: {e}")
            error_count += len(chunk)
            session.rollback()
    
    return {
        'total': total_paragraphs,
        'translated': translated_count,
        'errors': error_count
    }


def main():
    parser = argparse.ArgumentParser(
        description='Translate an entire chapter (all sections or all paragraphs)'
    )
    parser.add_argument(
        '--chapter',
        type=int,
        required=True,
        help='Chapter number to translate'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default='modern',
        help='Prompt name from config.yaml (default: modern)'
    )
    parser.add_argument(
        '--model-suffix',
        type=str,
        help='Suffix to add to prompt name for storage (e.g., "gpt5-mini")'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=50,
        help='Maximum paragraphs per chunk for large sections (default: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be translated without actually translating'
    )
    
    args = parser.parse_args()
    
    # Build the prompt name with optional suffix
    if args.model_suffix:
        prompt_name = f"{args.prompt}-{args.model_suffix}"
        print(f"Using prompt name with suffix: {prompt_name}")
    else:
        prompt_name = args.prompt
    
    print(f"Using OpenAI model: {config.openai_model}")
    print(f"Translation will be saved as prompt: '{prompt_name}'")
    print(f"Chunk size: {args.chunk_size} paragraphs\n")
    
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Find the chapter
        chapter = session.query(Chapter).filter(
            Chapter.chapter_number == args.chapter
        ).first()
        
        if not chapter:
            print(f"Error: Could not find chapter {args.chapter}")
            return
        
        print(f"Chapter {args.chapter}: {chapter.title}")
        print("=" * 80)
        
        # Check if chapter has sections
        sections = session.query(Section).filter(
            Section.chapter_id == chapter.id
        ).order_by(Section.section_number).all()
        
        if sections:
            # Chapter with sections
            print(f"Found {len(sections)} sections\n")
            
            total_stats = {'total': 0, 'translated': 0, 'errors': 0}
            
            for section in sections:
                # Get paragraphs for this section
                paragraphs = session.query(Paragraph).filter(
                    Paragraph.section_id == section.id
                ).order_by(Paragraph.paragraph_number).all()
                
                print(f"\nSection {section.section_number}: {section.title}")
                print(f"  Paragraphs: {len(paragraphs)}")
                
                if args.dry_run:
                    print(f"  [DRY RUN] Would translate {len(paragraphs)} paragraphs")
                    total_stats['total'] += len(paragraphs)
                    continue
                
                # Create translation service
                service = TranslationService(prompt_name=args.prompt)
                
                # Translate with chunking
                stats = translate_paragraphs(
                    session, service, paragraphs, prompt_name, args.chunk_size
                )
                
                total_stats['total'] += stats['total']
                total_stats['translated'] += stats['translated']
                total_stats['errors'] += stats['errors']
                
                print(f"  ✓ Section complete: {stats['translated']}/{stats['total']} translated")
        
        else:
            # Chapter without sections
            paragraphs = session.query(Paragraph).filter(
                Paragraph.chapter_id == chapter.id,
                Paragraph.section_id == None
            ).order_by(Paragraph.paragraph_number).all()
            
            print(f"No sections - translating {len(paragraphs)} paragraphs directly\n")
            
            if args.dry_run:
                print(f"[DRY RUN] Would translate {len(paragraphs)} paragraphs")
                total_stats = {'total': len(paragraphs), 'translated': 0, 'errors': 0}
            else:
                # Create translation service
                service = TranslationService(prompt_name=args.prompt)
                
                # Translate with chunking
                total_stats = translate_paragraphs(
                    session, service, paragraphs, prompt_name, args.chunk_size
                )
        
        # Summary
        print("\n" + "=" * 80)
        print("Chapter Translation Summary")
        print("=" * 80)
        print(f"Chapter: {chapter.title}")
        print(f"Model: {config.openai_model}")
        print(f"Prompt: {prompt_name}")
        print(f"Total paragraphs: {total_stats['total']}")
        print(f"Translated: {total_stats['translated']}")
        print(f"Errors: {total_stats['errors']}")
        
        if total_stats['translated'] > 0 and not args.dry_run:
            print(f"\n✓ Successfully translated {total_stats['translated']} paragraphs!")
            print(f"\nTo export this chapter:")
            print(f"  python -m src.pipeline.step3_export --prompt {prompt_name} --chapter {args.chapter}")
    
    finally:
        session.close()


if __name__ == '__main__':
    main()

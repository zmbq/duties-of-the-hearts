"""
Translate the entire book - all chapters and sections.

This script handles:
- All 12 chapters with their sections (or direct paragraphs)
- Large sections (breaks into chunks)
- Skip already-translated paragraphs (configurable)
- Progress tracking and error recovery
"""

import argparse
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import init_db, Chapter, Section, Paragraph, Translation
from src.utils import config
from src.pipeline.step2_translate import TranslationService


def chunk_paragraphs(paragraphs: List[Paragraph], max_chunk_size: int = 20) -> List[List[Paragraph]]:
    """
    Break paragraphs into chunks for large sections.
    
    Args:
        paragraphs: List of paragraphs to chunk
        max_chunk_size: Maximum paragraphs per chunk (default: 20)
        
    Returns:
        List of paragraph chunks
    """
    chunks = []
    for i in range(0, len(paragraphs), max_chunk_size):
        chunks.append(paragraphs[i:i + max_chunk_size])
    return chunks


def filter_untranslated(
    session: Session,
    paragraphs: List[Paragraph],
    prompt_name: str
) -> List[Paragraph]:
    """
    Filter out paragraphs that already have translations.
    
    Args:
        session: Database session
        paragraphs: List of paragraphs to check
        prompt_name: Translation prompt name
        
    Returns:
        List of paragraphs without translations
    """
    if not paragraphs:
        return []
    
    # Get IDs of paragraphs that already have this translation
    translated_ids = session.query(Translation.paragraph_id).filter(
        Translation.paragraph_id.in_([p.id for p in paragraphs]),
        Translation.prompt_name == prompt_name
    ).all()
    
    translated_id_set = {tid[0] for tid in translated_ids}
    
    # Return only untranslated paragraphs
    return [p for p in paragraphs if p.id not in translated_id_set]


def translate_paragraphs(
    session: Session,
    service: TranslationService,
    paragraphs: List[Paragraph],
    prompt_name: str,
    max_chunk_size: int = 20,
    force_retranslate: bool = False
) -> dict:
    """
    Translate a list of paragraphs, chunking if necessary.
    
    Args:
        session: Database session
        service: TranslationService instance
        paragraphs: List of paragraphs to translate
        prompt_name: Name to save translations under
        max_chunk_size: Maximum paragraphs per chunk
        force_retranslate: If True, re-translate even if translation exists
        
    Returns:
        Dictionary with success count and errors
    """
    total_paragraphs = len(paragraphs)
    
    if total_paragraphs == 0:
        return {'total': 0, 'translated': 0, 'errors': 0, 'skipped': 0}
    
    # Filter out already-translated paragraphs unless force_retranslate
    if not force_retranslate:
        untranslated = filter_untranslated(session, paragraphs, prompt_name)
        already_translated = total_paragraphs - len(untranslated)
        
        if already_translated > 0:
            print(f"  ℹ️  {already_translated} paragraphs already translated (skipping)")
        
        if not untranslated:
            return {
                'total': total_paragraphs,
                'translated': 0,
                'errors': 0,
                'skipped': already_translated
            }
        
        paragraphs = untranslated
    
    translated_count = 0
    error_count = 0
    
    # Check if we need to chunk
    if len(paragraphs) > max_chunk_size:
        chunks = chunk_paragraphs(paragraphs, max_chunk_size)
        print(f"  📦 Breaking into {len(chunks)} chunks of ~{max_chunk_size} paragraphs each")
    else:
        chunks = [paragraphs]
    
    # Translate each chunk
    for chunk_idx, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f"\n  📦 Chunk {chunk_idx}/{len(chunks)}: {len(chunk)} paragraphs")
        
        try:
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
    
    skipped = total_paragraphs - len(paragraphs) if not force_retranslate else 0
    
    return {
        'total': total_paragraphs,
        'translated': translated_count,
        'errors': error_count,
        'skipped': skipped
    }


def main():
    parser = argparse.ArgumentParser(
        description='Translate the entire book - all chapters and sections'
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
        default=20,
        help='Maximum paragraphs per chunk for large sections (default: 20)'
    )
    parser.add_argument(
        '--force-retranslate',
        action='store_true',
        help='Re-translate paragraphs even if translation already exists'
    )
    parser.add_argument(
        '--start-chapter',
        type=int,
        default=1,
        help='Start from this chapter number (default: 1)'
    )
    parser.add_argument(
        '--end-chapter',
        type=int,
        help='End at this chapter number (default: translate all remaining)'
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
    print(f"Chunk size: {args.chunk_size} paragraphs")
    print(f"Force re-translate: {args.force_retranslate}")
    if args.dry_run:
        print("DRY RUN MODE - No actual translation will occur")
    print("\n" + "=" * 80)
    
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Get all chapters
        all_chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()
        
        # Filter by start/end chapter
        chapters = [
            c for c in all_chapters
            if c.chapter_number >= args.start_chapter and
               (args.end_chapter is None or c.chapter_number <= args.end_chapter)
        ]
        
        if not chapters:
            print("No chapters found in the specified range")
            return
        
        print(f"Translating {len(chapters)} chapters (#{args.start_chapter} to #{chapters[-1].chapter_number})")
        print("=" * 80)
        
        # Initialize service (not in dry-run)
        service = None if args.dry_run else TranslationService(prompt_name=args.prompt)
        
        # Track overall statistics
        overall_stats = {
            'total': 0,
            'translated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Process each chapter
        for chapter in chapters:
            print(f"\n{'=' * 80}")
            print(f"Chapter {chapter.chapter_number}: {chapter.title}")
            print("=" * 80)
            
            # Check if chapter has sections
            sections = session.query(Section).filter(
                Section.chapter_id == chapter.id
            ).order_by(Section.section_number).all()
            
            if sections:
                # Chapter with sections
                print(f"Found {len(sections)} sections\n")
                
                for section in sections:
                    # Get paragraphs for this section
                    paragraphs = session.query(Paragraph).filter(
                        Paragraph.section_id == section.id
                    ).order_by(Paragraph.paragraph_number).all()
                    
                    print(f"\nSection {section.section_number}: {section.title}")
                    print(f"  Paragraphs: {len(paragraphs)}")
                    
                    if args.dry_run:
                        untranslated = filter_untranslated(session, paragraphs, prompt_name)
                        print(f"  [DRY RUN] Would translate {len(untranslated)} paragraphs ({len(paragraphs) - len(untranslated)} already translated)")
                        overall_stats['total'] += len(paragraphs)
                        overall_stats['skipped'] += len(paragraphs) - len(untranslated)
                        continue
                    
                    # Translate with chunking
                    stats = translate_paragraphs(
                        session, service, paragraphs, prompt_name,
                        args.chunk_size, args.force_retranslate
                    )
                    
                    overall_stats['total'] += stats['total']
                    overall_stats['translated'] += stats['translated']
                    overall_stats['errors'] += stats['errors']
                    overall_stats['skipped'] += stats['skipped']
                    
                    print(f"  ✓ Section complete: {stats['translated']}/{stats['total']} translated, {stats['skipped']} skipped")
            
            else:
                # Chapter without sections
                paragraphs = session.query(Paragraph).filter(
                    Paragraph.chapter_id == chapter.id,
                    Paragraph.section_id == None
                ).order_by(Paragraph.paragraph_number).all()
                
                print(f"No sections - {len(paragraphs)} paragraphs directly\n")
                
                if args.dry_run:
                    untranslated = filter_untranslated(session, paragraphs, prompt_name)
                    print(f"[DRY RUN] Would translate {len(untranslated)} paragraphs ({len(paragraphs) - len(untranslated)} already translated)")
                    overall_stats['total'] += len(paragraphs)
                    overall_stats['skipped'] += len(paragraphs) - len(untranslated)
                    continue
                
                # Translate with chunking
                stats = translate_paragraphs(
                    session, service, paragraphs, prompt_name,
                    args.chunk_size, args.force_retranslate
                )
                
                overall_stats['total'] += stats['total']
                overall_stats['translated'] += stats['translated']
                overall_stats['errors'] += stats['errors']
                overall_stats['skipped'] += stats['skipped']
                
                print(f"✓ Chapter complete: {stats['translated']}/{stats['total']} translated, {stats['skipped']} skipped")
        
        # Final summary
        print("\n" + "=" * 80)
        print("BOOK TRANSLATION SUMMARY")
        print("=" * 80)
        print(f"Model: {config.openai_model}")
        print(f"Prompt: {prompt_name}")
        print(f"Chapters: {len(chapters)} ({args.start_chapter} to {chapters[-1].chapter_number})")
        print(f"Total paragraphs: {overall_stats['total']}")
        print(f"Translated: {overall_stats['translated']}")
        print(f"Skipped (already done): {overall_stats['skipped']}")
        print(f"Errors: {overall_stats['errors']}")
        
        if overall_stats['translated'] > 0 and not args.dry_run:
            success_rate = (overall_stats['translated'] / (overall_stats['translated'] + overall_stats['errors'])) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print(f"\n✓ Successfully translated {overall_stats['translated']} paragraphs!")
            print(f"\nTo export the entire book:")
            print(f"  # Create a script to export all chapters and combine them")
    
    finally:
        session.close()


if __name__ == '__main__':
    main()

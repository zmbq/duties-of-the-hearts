"""
Export the entire book to DOCX format.

This script creates complete book documents with all chapters and sections:
- Version with original text (side-by-side translation)
- Version with translation only
"""

import argparse
from pathlib import Path
from sqlalchemy.orm import Session

from src.models import init_db, Chapter, Section
from src.utils import config
from src.pipeline.step3_export import DocumentExporter


def export_complete_book(
    session: Session,
    prompt_name: str,
    show_original: bool,
    output_file: Path
):
    """
    Export the complete book with all chapters and sections.
    
    Args:
        session: Database session
        prompt_name: Translation prompt name to export
        show_original: Whether to show original text alongside translation
        output_file: Path to save the document
    """
    print(f"\nCreating book document...")
    print(f"  Prompt: {prompt_name}")
    print(f"  Show original: {show_original}")
    print(f"  Output: {output_file}")
    
    # Create exporter
    exporter = DocumentExporter(show_original=show_original, prompt_name=prompt_name)
    
    # Add title page
    title = exporter.doc.add_heading(level=0)
    title_run = title.add_run("חובות הלבבות")
    title_run.font.name = 'David'
    title_run.font.size = 24
    exporter._set_paragraph_rtl(title)
    
    subtitle = exporter.doc.add_paragraph()
    if show_original:
        subtitle_run = subtitle.add_run(exporter._fix_rtl_text("תרגום לעברית מודרנית (עם מקור)"))
    else:
        subtitle_run = subtitle.add_run(exporter._fix_rtl_text("תרגום לעברית מודרנית"))
    subtitle_run.font.name = 'David'
    subtitle_run.font.size = 16
    subtitle_run.italic = True
    exporter._set_paragraph_rtl(subtitle)
    
    author = exporter.doc.add_paragraph()
    author_run = author.add_run("רבנו בחיי אבן פקודה")
    author_run.font.name = 'David'
    author_run.font.size = 14
    exporter._set_paragraph_rtl(author)
    
    exporter.doc.add_page_break()
    
    # Get all chapters
    chapters = session.query(Chapter).order_by(Chapter.chapter_number).all()
    
    total_chapters = len(chapters)
    print(f"\n  Processing {total_chapters} chapters...")
    
    for idx, chapter in enumerate(chapters, 1):
        print(f"  [{idx}/{total_chapters}] {chapter.title}...")
        
        # Export the chapter
        exporter.export_chapter(session, chapter)
        
        # Add page break after each chapter (except the last)
        if idx < total_chapters:
            exporter.doc.add_page_break()
    
    # Save the document
    exporter.save(output_file)
    print(f"\n✓ Book export complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Export the entire translated book to DOCX format'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default='modern-gpt5-mini',
        help='Prompt name to export (default: modern-gpt5-mini)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (default: from config)'
    )
    parser.add_argument(
        '--basename',
        type=str,
        help='Base filename (default: duties_of_hearts_<prompt>)'
    )
    parser.add_argument(
        '--original-only',
        action='store_true',
        help='Only create version with original text'
    )
    parser.add_argument(
        '--translation-only',
        action='store_true',
        help='Only create version with translation only'
    )
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = config.output_dir
    
    # Determine base filename
    if args.basename:
        basename = args.basename
    else:
        # Remove special characters from prompt name for filename
        safe_prompt = args.prompt.replace('/', '_').replace('\\', '_')
        basename = f"duties_of_hearts_{safe_prompt}"
    
    print("=" * 80)
    print("EXPORTING COMPLETE BOOK")
    print("=" * 80)
    print(f"Prompt: {args.prompt}")
    print(f"Output directory: {output_dir}")
    
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Count total chapters for info
        total_chapters = session.query(Chapter).count()
        print(f"Total chapters: {total_chapters}")
        
        # Determine which versions to create
        create_with_original = not args.translation_only
        create_translation_only = not args.original_only
        
        versions_to_create = []
        if create_with_original:
            versions_to_create.append("with original")
        if create_translation_only:
            versions_to_create.append("translation only")
        
        print(f"Creating versions: {', '.join(versions_to_create)}")
        print("=" * 80)
        
        # Create version with original text
        if create_with_original:
            print("\n" + "=" * 80)
            print("VERSION 1: WITH ORIGINAL TEXT (SIDE-BY-SIDE)")
            print("=" * 80)
            output_file = output_dir / f"{basename}_with_original.docx"
            export_complete_book(
                session=session,
                prompt_name=args.prompt,
                show_original=True,
                output_file=output_file
            )
        
        # Create version with translation only
        if create_translation_only:
            print("\n" + "=" * 80)
            print("VERSION 2: TRANSLATION ONLY")
            print("=" * 80)
            output_file = output_dir / f"{basename}_translation_only.docx"
            export_complete_book(
                session=session,
                prompt_name=args.prompt,
                show_original=False,
                output_file=output_file
            )
        
        # Final summary
        print("\n" + "=" * 80)
        print("EXPORT SUMMARY")
        print("=" * 80)
        print(f"Prompt: {args.prompt}")
        print(f"Output directory: {output_dir}")
        
        if create_with_original:
            print(f"✓ With original: {basename}_with_original.docx")
        if create_translation_only:
            print(f"✓ Translation only: {basename}_translation_only.docx")
        
        print("\n✓ All exports complete! Open the files in Word to review.")
    
    finally:
        session.close()


if __name__ == '__main__':
    main()

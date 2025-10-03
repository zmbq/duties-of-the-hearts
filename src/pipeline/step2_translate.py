"""
Step 2: Translate paragraphs using OpenAI API.

This script translates medieval Hebrew text to modern Hebrew while:
- Preserving biblical/Talmudic quotes unchanged
- Maintaining exact paragraph structure (1:1 mapping)
- Handling sections in manageable chunks
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI

from src.models import init_db, Chapter, Section, Paragraph, Translation
from src.utils import config


class TranslationService:
    """Service for translating text using OpenAI API."""
    
    def __init__(self, prompt_name: str = "modern"):
        """
        Initialize the translation service.
        
        Args:
            prompt_name: Name of the prompt to use from config.yaml
        """
        self.client = OpenAI(api_key=config.openai_api_key)
        self.prompt_config = config.get_prompt(prompt_name)
        self.prompt_name = prompt_name
        self.model = config.openai_model
        
        if not self.prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found in config.yaml")
    
    def translate_section(self, paragraphs: List[Paragraph]) -> List[str]:
        """
        Translate a section (list of paragraphs) to modern Hebrew.
        
        Args:
            paragraphs: List of Paragraph objects to translate
            
        Returns:
            List of translated paragraph texts (same length as input)
        """
        if not paragraphs:
            return []
        
        # Build the input text with numbered paragraphs
        numbered_input = []
        for i, para in enumerate(paragraphs, 1):
            numbered_input.append(f"[{i}] {para.text}")
        
        input_text = "\n\n".join(numbered_input)
        
        # Create the system prompt
        system_prompt = self.prompt_config.get('system_prompt', '')
        
        # Add strict instructions about maintaining structure and quotes
        enhanced_system_prompt = f"""{system_prompt}

CRITICAL INSTRUCTIONS:
1. You MUST return EXACTLY {len(paragraphs)} translated paragraphs, numbered [1] through [{len(paragraphs)}]
2. Each paragraph must start with its number in brackets: [1], [2], [3], etc.
3. DO NOT translate biblical quotes, Talmudic quotes, or any quoted text from traditional sources
4. Biblical verses (תהלים, משלי, ישעיה, דברים, etc.) must remain in their original medieval Hebrew
5. Talmudic/Midrashic quotes must remain in their original form
6. Only translate the author's own explanatory text
7. Maintain the exact same paragraph structure - no merging or splitting
8. If a paragraph contains both a quote and explanation, translate only the explanation

Example format:
[1] translated first paragraph...
[2] translated second paragraph...
[3] translated third paragraph...
"""
        
        # User message
        user_message = f"""Translate the following {len(paragraphs)} paragraphs from medieval Hebrew to modern Hebrew.
Remember: DO NOT translate quotes from Torah, Prophets, Writings, Talmud, or Midrash.

{input_text}"""
        
        print(f"  Calling OpenAI API ({self.model})...")
        print(f"  Input: {len(paragraphs)} paragraphs, ~{len(input_text)} characters")
        
        # Call OpenAI API
        # Note: gpt-5-mini and newer models use max_completion_tokens instead of max_tokens
        # and don't support custom temperature
        api_params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_message}
            ],
        }
        
        # Check if this is a newer model that has restrictions
        is_new_model = any(m in self.model for m in ['gpt-5', 'o1', 'o3'])
        
        if is_new_model:
            # Newer reasoning models: use max_completion_tokens and default temperature
            # Note: Reasoning models use many tokens for internal reasoning, so we need a much higher limit
            # For gpt-5-mini, reasoning tokens can be substantial (2000-6000+)
            # We need to ensure: reasoning_tokens + output_tokens <= max_completion_tokens
            # For safety, use a very high limit to prevent truncation
            api_params["max_completion_tokens"] = config.get('openai.max_tokens', 4000) * 5  # 5x for large batches
        else:
            # Older models: use max_tokens and custom temperature
            api_params["temperature"] = config.get('openai.temperature', 0.3)
            api_params["max_tokens"] = config.get('openai.max_tokens', 4000)
        
        response = self.client.chat.completions.create(**api_params)
        
        # Extract the response
        translated_text = response.choices[0].message.content
        
        # Debug: Check if we have a refusal or other issue
        if hasattr(response.choices[0].message, 'refusal') and response.choices[0].message.refusal:
            print(f"  Model refused to respond: {response.choices[0].message.refusal}")
            raise ValueError(f"Model refused: {response.choices[0].message.refusal}")
        
        if not translated_text:
            print(f"  Warning: Empty response from model!")
            print(f"  Response object: {response}")
            print(f"  Finish reason: {response.choices[0].finish_reason}")
            raise ValueError("Model returned empty response")
        
        print(f"  Response: ~{len(translated_text)} characters")
        print(f"  Tokens used: {response.usage.prompt_tokens} input, {response.usage.completion_tokens} output")
        
        # Parse the numbered paragraphs
        translations = self._parse_numbered_response(translated_text, len(paragraphs))
        
        if len(translations) != len(paragraphs):
            raise ValueError(
                f"Translation mismatch! Expected {len(paragraphs)} paragraphs, got {len(translations)}. "
                f"This is a critical error - please check the LLM response."
            )
        
        return translations
    
    def _parse_numbered_response(self, response: str, expected_count: int) -> List[str]:
        """
        Parse numbered paragraphs from LLM response.
        
        Args:
            response: Raw text from LLM with numbered paragraphs
            expected_count: Expected number of paragraphs
            
        Returns:
            List of paragraph texts (without numbers)
        """
        import re
        
        # Split by paragraph numbers [1], [2], etc.
        # Pattern matches [number] at the start of a line
        parts = re.split(r'\n*\[(\d+)\]\s*', response)
        
        # parts[0] is any text before [1], parts[1] is "1", parts[2] is text after [1], etc.
        # We want parts[2], parts[4], parts[6], etc. (the actual text)
        paragraphs = []
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                paragraph_num = int(parts[i])
                paragraph_text = parts[i + 1].strip()
                paragraphs.append(paragraph_text)
        
        # Validate we got the right number
        if len(paragraphs) != expected_count:
            print(f"⚠️  Warning: Expected {expected_count} paragraphs, parsed {len(paragraphs)}")
            print(f"Raw response (full):\n{response}\n")
            print(f"Raw response preview:\n{response[:500]}...")
        
        return paragraphs


def translate_section_to_db(
    session: Session,
    service: TranslationService,
    section: Optional[Section] = None,
    chapter: Optional[Chapter] = None,
    max_paragraphs: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, any]:
    """
    Translate a section or chapter and save to database.
    
    Args:
        session: Database session
        service: TranslationService instance
        section: Section to translate (if has sections)
        chapter: Chapter to translate (if no sections)
        max_paragraphs: Maximum paragraphs to translate (for testing)
        dry_run: If True, don't save to database
        
    Returns:
        Dict with statistics
    """
    # Get paragraphs
    if section:
        query = session.query(Paragraph).filter(
            Paragraph.section_id == section.id
        ).order_by(Paragraph.paragraph_number)
        location = f"{section.chapter.title} → {section.title}"
    elif chapter:
        query = session.query(Paragraph).filter(
            Paragraph.chapter_id == chapter.id,
            Paragraph.section_id == None
        ).order_by(Paragraph.paragraph_number)
        location = chapter.title
    else:
        raise ValueError("Must provide either section or chapter")
    
    if max_paragraphs:
        query = query.limit(max_paragraphs)
    
    paragraphs = query.all()
    
    if not paragraphs:
        print(f"  No paragraphs to translate in {location}")
        return {"translated": 0, "skipped": 0, "errors": 0}
    
    print(f"\n{'='*80}")
    print(f"Translating: {location}")
    print(f"Paragraphs: {len(paragraphs)}")
    print(f"Prompt: {service.prompt_name}")
    print(f"{'='*80}")
    
    # Translate
    try:
        translations = service.translate_section(paragraphs)
        
        # Save to database
        saved = 0
        for para, trans_text in zip(paragraphs, translations):
            if dry_run:
                print(f"\n[Paragraph {para.paragraph_number}]")
                print(f"Original: {para.text[:100]}...")
                print(f"Translated: {trans_text[:100]}...")
            else:
                # Check if translation already exists
                existing = session.query(Translation).filter(
                    Translation.paragraph_id == para.id,
                    Translation.prompt_name == service.prompt_name
                ).first()
                
                if existing:
                    # Update existing translation
                    existing.translated_text = trans_text
                    existing.model = service.model
                    existing.created_at = datetime.now()
                else:
                    # Create new translation
                    translation = Translation(
                        paragraph_id=para.id,
                        prompt_name=service.prompt_name,
                        translated_text=trans_text,
                        model=service.model
                    )
                    session.add(translation)
                
                saved += 1
        
        if not dry_run:
            session.commit()
            print(f"✓ Saved {saved} translations to database")
        
        return {"translated": len(translations), "skipped": 0, "errors": 0}
    
    except Exception as e:
        print(f"✗ Error during translation: {e}")
        session.rollback()
        return {"translated": 0, "skipped": 0, "errors": 1}


def main():
    """Main function - translate a test section."""
    print("Starting translation process...")
    
    # Initialize database
    engine, SessionLocal = init_db(config.database_url)
    session = SessionLocal()
    
    try:
        # Initialize translation service
        service = TranslationService(prompt_name="modern")
        
        # Find the test section: Chapter 6, Section 1 (8 paragraphs)
        # "שער חמישי - שער ייחוד המעשה → הקדמה"
        chapter = session.query(Chapter).filter(
            Chapter.chapter_number == 6
        ).first()
        
        if not chapter:
            print("Error: Could not find chapter 6")
            return
        
        section = session.query(Section).filter(
            Section.chapter_id == chapter.id,
            Section.section_number == 1
        ).first()
        
        if not section:
            print("Error: Could not find section 1 in chapter 6")
            return
        
        # Check paragraph count
        para_count = session.query(Paragraph).filter(
            Paragraph.section_id == section.id
        ).count()
        
        print(f"Found test section: {chapter.title} → {section.title}")
        print(f"Contains {para_count} paragraphs")
        
        # Translate (not a dry run - we'll save to DB)
        stats = translate_section_to_db(
            session=session,
            service=service,
            section=section,
            dry_run=False  # Set to True to preview without saving
        )
        
        print(f"\n{'='*80}")
        print("Translation Summary")
        print(f"{'='*80}")
        print(f"Translated: {stats['translated']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['translated'] > 0:
            print(f"\n✓ Successfully translated {stats['translated']} paragraphs!")
            print(f"  Run 'python -m tests.verify_translations' to review results")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

# Duties of the Hearts - Translation Project

A Python pipeline for translating the medieval Hebrew philosophical text "Duties of the Heart" (חובות הלבבות) into modern Hebrew using AI.

## Project Overview

This project provides a complete pipeline for:
1. **Importing** the original book from JSON format into a SQLite database
2. **Translating** the text from medieval to modern Hebrew using OpenAI's GPT models
3. **Exporting** the translated text to Word (DOCX) documents

The system supports multiple translation prompts/styles, allowing you to generate different versions of the translation (literal, modern, simplified, etc.).

## Setup Instructions

### 1. Prerequisites

- Python 3.13+ (already have `env/` virtual environment)
- Poetry (for dependency management)
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### 2. Install Dependencies

```powershell
poetry install
```

### 3. Configure API Key (IMPORTANT!)

The OpenAI API key is stored in a `.env` file that is **NOT** committed to git for security.

**On Windows, follow these steps:**

1. Copy the example environment file:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` in your favorite editor:
   ```powershell
   notepad .env
   ```

3. Replace `your-openai-api-key-here` with your actual OpenAI API key:
   ```
   OPENAI_API_KEY=sk-proj-...your-actual-key-here...
   ```

4. Save and close the file.

**That's it!** The `.env` file is in `.gitignore` so it won't be committed to git.

### 4. Verify Configuration

Test that everything is configured correctly:

```powershell
python tests\test_config.py
```

You should see output showing:
- Project root
- Config file location
- Database URL
- OpenAI model
- Output directory
- Available prompts
- API key status (masked)

## Project Structure

```
duties-of-the-hearts/
├── assets/                          # Original book JSON files
│   └── Duties of the Heart - he - Vocalized Edition (1).json
├── src/
│   ├── models/                      # Database models
│   │   ├── __init__.py
│   │   └── database.py             # SQLAlchemy models
│   ├── pipeline/                    # Translation pipeline
│   │   ├── step1_import.py         # Import JSON to database
│   │   ├── step2_translate.py      # Translate using OpenAI (TODO)
│   │   └── step3_export.py         # Export to DOCX (TODO)
│   ├── services/                    # Service layers (TODO)
│   │   ├── llm_service.py          # OpenAI integration
│   │   └── document_service.py     # Document generation
│   └── utils/                       # Utilities
│       └── __init__.py             # Configuration management
├── tests/                           # Test scripts
│   ├── test_config.py              # Configuration system tests
│   ├── verify_import.py            # Database import verification
│   └── test_clean_text.py          # HTML tag removal verification
├── output/                          # Generated documents (gitignored)
├── .env                            # YOUR API keys (gitignored, create from .env.example)
├── .env.example                    # Template for .env
├── config.yaml                     # Application settings
├── pyproject.toml                  # Dependencies
└── README.md                       # This file
```

## Configuration Files

### `.env` (Secret - Not in Git)
Contains sensitive information like API keys:
- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `OPENAI_MODEL` - Optional model override
- `DATABASE_URL` - Optional database connection string

### `config.yaml` (Public - In Git)
Contains non-sensitive application settings:
- OpenAI model defaults and parameters
- Translation prompts (literal, modern, simplified)
- Document export settings
- Pipeline configuration

You can edit `config.yaml` to:
- Add new translation prompts
- Adjust temperature and max tokens
- Change document formatting
- Modify batch sizes and delays

## Database Schema

The database has four main tables:

1. **`chapters`** - Main chapters of the book
   - `id`, `title`, `chapter_number`

2. **`sections`** - Sections within chapters (optional)
   - `id`, `chapter_id`, `title`, `section_number`

3. **`paragraphs`** - Original Hebrew text
   - `id`, `chapter_id`, `section_id`, `paragraph_number`, `text`

4. **`translations`** - Modern Hebrew translations
   - `id`, `paragraph_id`, `prompt_name`, `translated_text`, `model`

## Usage (Coming Soon)

### Step 1: Import the Book

```powershell
python -m src.pipeline.step1_import
```

### Step 2: Translate

```powershell
# Translate using the 'literal' prompt
python -m src.pipeline.step2_translate --prompt literal

# Or use a different prompt
python -m src.pipeline.step2_translate --prompt modern
```

### Step 3: Export to Document

```powershell
# Export with a specific translation
python -m src.pipeline.step3_export --prompt literal --output "duties_literal.docx"
```

## Development Status

- [x] Project structure
- [x] Database models
- [x] Configuration management
- [x] Dependency installation
- [x] JSON import pipeline (Step 1 complete)
- [x] HTML tag cleaning
- [x] Hebrew title extraction from schema
- [ ] OpenAI translation service
- [ ] Document export
- [ ] CLI interface
- [ ] Error handling & retry logic
- [ ] Progress tracking

## Testing

Run tests to verify the system:

```powershell
# Test configuration
python -m tests.test_config

# Verify database import
python -m tests.verify_import

# Check for clean text (no HTML tags)
python -m tests.test_clean_text
```

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

The original "Duties of the Heart" text is in the Public Domain.

This translation tool is provided as-is for educational purposes.

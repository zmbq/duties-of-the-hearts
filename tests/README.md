# Test Scripts Organization

All test scripts have been moved to the `tests/` folder for better project organization.

## Available Tests

### 1. Configuration Test (`test_config.py`)
Tests the configuration system to ensure:
- `.env` file is loaded correctly
- `config.yaml` is parsed properly
- OpenAI API key is accessible
- All paths are correctly resolved

**Run:**
```powershell
python -m tests.test_config
```

### 2. Import Verification (`verify_import.py`)
Verifies the database import results:
- Shows total counts (chapters, sections, paragraphs)
- Lists all chapters with their Hebrew titles
- Displays section breakdown
- Shows sample paragraph

**Run:**
```powershell
python -m tests.verify_import
```

### 3. Clean Text Test (`test_clean_text.py`)
Verifies HTML tags have been removed:
- Checks first 10 paragraphs for HTML tags
- Reports any remaining tags
- Shows sample clean paragraphs

**Run:**
```powershell
python -m tests.test_clean_text
```

## Test Results

All tests are currently passing ✅:
- Configuration system working correctly
- 12 chapters, 23 sections, 2,328 paragraphs imported
- All HTML tags successfully removed from text

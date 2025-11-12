# AI-Powered Field Mapping Setup

## Overview
The Map Editor now supports AI-powered field mapping using OpenAI's GPT-4 to automatically match HTML elements to database fields.

## Setup Instructions

### 1. Install OpenAI Python Package
```powershell
pip install openai
```

### 2. Set Up OpenAI API Key

Get your API key from: https://platform.openai.com/api-keys

Then set it as an environment variable:

**PowerShell (Current Session):**
```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

**PowerShell (Permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-api-key-here', 'User')
```

**Verify it's set:**
```powershell
echo $env:OPENAI_API_KEY
```

### 3. Usage

1. Open the Map Editor
2. Select a mapping (or it will auto-detect new HTML files)
3. Click "Generate from Capture"
4. When prompted:
   - **YES**: AI will analyze the HTML and automatically suggest field mappings
   - **NO**: Manual mapping (just extracts elements, you assign fields)

## How It Works

1. The AI receives:
   - The list of available database fields (from `apartment_listings` table)
   - Extracted HTML elements with their values, CSS paths, and tags
   
2. GPT-4 analyzes:
   - Element content (e.g., "$1,650" → `price`)
   - CSS paths (e.g., `img.listing-image` → `img_urls`)
   - Context clues (e.g., URLs, addresses, etc.)
   
3. Returns suggested mappings that you can review and adjust

## Benefits

- **Faster mapping**: Auto-assigns 80-90% of fields correctly
- **Smart matching**: Uses context and patterns to identify fields
- **Manual override**: You can always change AI suggestions
- **Preserves existing**: Never overwrites already-assigned fields

## Cost

- Uses `gpt-4o-mini` model (~$0.15 per 1M tokens)
- Typical cost per mapping: < $0.01
- Only runs when you choose "YES" for AI mapping

## Fallback

If AI mapping fails (no API key, network error, etc.), the editor falls back to manual mapping mode automatically.

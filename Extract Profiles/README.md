# Extract Profiles System

This directory contains extraction profiles for different website types.

## Profile Structure

Each profile is a JSON file with the following structure:

```json
{
  "profile_name": "ProfileName",
  "detection": {
    "domain_patterns": ["domain1.com", "domain2.com"],
    "html_markers": ["unique-class", "unique-id"]
  },
  "extraction": {
    "container_selector": "div[id='container'], div.container-class",
    "listing_selector": "div.listing-item",
    "fields": {
      "field_name": {
        "selector": "CSS selector",
        "attribute": "text|href|src",
        "pattern": "regex pattern (optional)"
      }
    }
  },
  "openai_prompt_template": "Custom prompt with {html} placeholder"
}
```

## Detection

The system automatically detects which profile to use based on:
1. **Domain patterns**: Matches against the URL found in the HTML
2. **HTML markers**: Searches for unique class names, IDs, or elements

Profiles are scored:
- +10 points for each matching domain pattern
- +5 points for each matching HTML marker
- Profile with highest score (minimum 5) is selected

## Current Profiles

### appfolio.json
For websites using AppFolio property management system:
- Domain: `appfolio.com`
- Markers: `js-listings-container`, `js-listing-item`, `listing-item result`

### wix.json
For websites built with Wix:
- Domain: `wixsite.com`, `wix.com`
- Markers: `wixui-repeater`, `fluid-columns-repeater`, `wixui-rich-text`

### default.json
Fallback profile when no specific match is found.

## Adding New Profiles

1. Create a new `.json` file in `Extract Profiles/Network/`
2. Define detection criteria (domain patterns and HTML markers)
3. Specify extraction selectors for the container and listing items
4. Define field extraction rules with CSS selectors
5. Create a custom OpenAI prompt template that:
   - Explains the website structure
   - Warns against extracting filter options or navigation
   - Uses `{html}` placeholder for the HTML content

## Testing Profiles

The system logs which profile is detected:
- Check browser console or job status for "Detected profile: [name]"
- Verify extraction results match expected output
- Adjust detection criteria if wrong profile is selected

## Profile Priority

If multiple profiles match, the one with the highest score wins. To ensure a profile is preferred:
- Add more specific domain patterns
- Add more unique HTML markers
- Use patterns that appear frequently in the HTML

"""
Test OpenAI Vision API with 2 sample parcel images
"""

import os

# Check if API key is set
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("❌ OPENAI_API_KEY not set!")
    print("\nTo set your OpenAI API key, run:")
    print('  $env:OPENAI_API_KEY="sk-your-api-key-here"')
    print("\nOr add it permanently to your environment variables.")
else:
    print(f"✅ OPENAI_API_KEY is set (starts with: {api_key[:20]}...)")
    print("\nReady to process images!")
    print("\nTo run the full script:")
    print("  python process_with_openai.py")

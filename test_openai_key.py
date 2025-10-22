#!/usr/bin/env python3
"""
Quick test to validate OpenAI API key from environment
"""

import os
import sys

def test_openai_key():
    """Test if the OpenAI API key from environment is valid"""

    print("=" * 80)
    print("🔑 OpenAI API Key Validation Test")
    print("=" * 80)

    # Step 1: Check if key exists in environment
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("\n❌ OPENAI_API_KEY not found in environment!")
        print("\n💡 Set it with:")
        print("   export OPENAI_API_KEY='your-actual-key-here'")
        return False

    # Mask the key for display
    if len(api_key) > 10:
        masked_key = f"{api_key[:7]}...{api_key[-4:]}"
    else:
        masked_key = "***"

    print(f"\n✅ OPENAI_API_KEY found in environment")
    print(f"   Key (masked): {masked_key}")
    print(f"   Key length: {len(api_key)} characters")

    # Step 2: Check key format
    if not api_key.startswith('sk-'):
        print(f"\n⚠️  Warning: Key doesn't start with 'sk-' (starts with: {api_key[:5]})")
        print("   OpenAI keys should start with 'sk-'")

    # Step 3: Try to import openai
    try:
        import openai
        print(f"\n✅ openai library installed (version: {openai.__version__})")
    except ImportError:
        print("\n❌ openai library not installed!")
        print("\n💡 Install with:")
        print("   pip install openai")
        return False

    # Step 4: Test the API key with a minimal request
    print("\n🔄 Testing API key with OpenAI API call...")
    print("   Making request to: /v1/models endpoint (list models)")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Try to list models (minimal API call)
        models = client.models.list()

        print("\n✅ API Key is VALID!")
        print(f"   Successfully connected to OpenAI API")
        print(f"   Available models: {len(list(models.data))}")

        # Show some models
        print("\n📋 Sample models available:")
        for i, model in enumerate(list(models.data)[:5]):
            print(f"   {i+1}. {model.id}")

        # Test with a minimal completion
        print("\n🔄 Testing with minimal completion request...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API test successful' in 3 words"}],
            max_tokens=10
        )

        result = response.choices[0].message.content
        print(f"✅ Completion test successful!")
        print(f"   Response: {result}")
        print(f"   Model used: {response.model}")
        print(f"   Tokens: {response.usage.total_tokens}")

        return True

    except Exception as e:
        error_str = str(e)
        print(f"\n❌ API Key INVALID or API Error!")
        print(f"   Error: {error_str}")

        # Provide helpful hints based on error
        if "401" in error_str or "Incorrect API key" in error_str:
            print("\n💡 This is an authentication error. The key is invalid or expired.")
            print("   1. Check if you copied the entire key (should start with 'sk-')")
            print("   2. Verify the key is active in your OpenAI dashboard")
            print("   3. Generate a new key at: https://platform.openai.com/api-keys")
        elif "429" in error_str:
            print("\n💡 Rate limit exceeded. The key is valid but you've hit usage limits.")
        elif "quota" in error_str.lower():
            print("\n💡 Quota exceeded. The key is valid but you're out of credits.")
            print("   Add credits at: https://platform.openai.com/account/billing")
        elif "organization" in error_str.lower():
            print("\n💡 Organization issue. Check your OpenAI organization settings.")

        return False

if __name__ == "__main__":
    print()
    success = test_openai_key()
    print("\n" + "=" * 80)

    if success:
        print("✅ RESULT: OpenAI API key is valid and working!")
        print("\n💡 You can now use Artemis with this key")
        sys.exit(0)
    else:
        print("❌ RESULT: OpenAI API key validation FAILED")
        print("\n💡 Fix the key before running Artemis pipeline")
        sys.exit(1)

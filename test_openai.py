#!/home/bbrelin/src/repos/salesforce/.venv/bin/python
"""Quick test script for OpenAI API"""

import os
from openai import OpenAI

def test_openai_api():
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return False

    print(f"✓ API key found: {api_key[:10]}...{api_key[-4:]}")

    try:
        # Initialize client
        client = OpenAI(api_key=api_key)
        print("✓ OpenAI client initialized")

        # Make a simple test call
        print("\n🔄 Testing API call with GPT-5 (latest model)...")
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2? Answer briefly."}
            ]
            # No token limit to see full response
        )

        # Extract response
        answer = response.choices[0].message.content

        print("\n✅ API Test Successful!")
        print(f"Response: {answer}")
        print(f"Response type: {type(answer)}")
        print(f"Response length: {len(answer) if answer else 0}")

        # Debug: show full message object
        print(f"\nFull message object:")
        print(f"  Role: {response.choices[0].message.role}")
        print(f"  Content: '{response.choices[0].message.content}'")
        print(f"  Finish reason: {response.choices[0].finish_reason}")

        print(f"\nUsage:")
        print(f"  - Prompt tokens: {response.usage.prompt_tokens}")
        print(f"  - Completion tokens: {response.usage.completion_tokens}")
        print(f"  - Total tokens: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"\n❌ API Test Failed!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI API Test")
    print("=" * 60)
    test_openai_api()

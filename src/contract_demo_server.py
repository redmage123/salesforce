#!/usr/bin/env python3
"""
Contract Summarization Demo Server

Flask backend with OpenAI GPT-4 integration for real-time contract field extraction.
Provides REST API for dynamic HTML demo.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI library not installed. Install with: pip install openai")

app = Flask(__name__)
CORS(app)  # Enable CORS for demo HTML page

# Initialize OpenAI client
if OPENAI_AVAILABLE:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
else:
    client = None


# JSON Schemas (same as notebook)
CONTRACT_SCHEMAS = {
    "master_services_agreement": {
        "type": "object",
        "required": [
            "contract_type",
            "vendor_name",
            "customer_name",
            "effective_date",
            "contract_end_date",
            "total_contract_value",
            "payment_terms"
        ],
        "properties": {
            "contract_type": {"type": "string"},
            "vendor_name": {"type": "string"},
            "vendor_address": {"type": "string"},
            "customer_name": {"type": "string"},
            "customer_address": {"type": "string"},
            "effective_date": {"type": "string", "format": "date"},
            "contract_end_date": {"type": "string", "format": "date"},
            "initial_term_months": {"type": "integer"},
            "renewal_term_months": {"type": "integer"},
            "auto_renewal": {"type": "boolean"},
            "total_contract_value": {"type": "number"},
            "annual_contract_value": {"type": "number"},
            "currency": {"type": "string"},
            "payment_terms": {"type": "string"},
            "payment_frequency": {"type": "string"},
            "services_description": {"type": "string"},
            "user_licenses": {"type": "integer"},
            "products": {"type": "array", "items": {"type": "string"}},
            "governing_law": {"type": "string"},
            "termination_notice_days": {"type": "integer"},
            "sla_uptime": {"type": "number"},
            "data_residency": {"type": "string"},
            "compliance_requirements": {"type": "array"},
            "primary_contact_vendor": {"type": "object"},
            "primary_contact_customer": {"type": "object"},
            "signatures": {"type": "array"},
            "key_terms": {"type": "array"},
            "risk_flags": {"type": "array"}
        }
    },
    "statement_of_work": {
        "type": "object",
        "required": [
            "contract_type",
            "customer_name",
            "project_name",
            "start_date",
            "total_contract_value"
        ],
        "properties": {
            "contract_type": {"type": "string"},
            "customer_name": {"type": "string"},
            "project_name": {"type": "string"},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "duration_weeks": {"type": "integer"},
            "total_contract_value": {"type": "number"},
            "payment_schedule": {"type": "array"},
            "scope_items": {"type": "array"},
            "deliverables": {"type": "array"},
            "milestones": {"type": "array"}
        }
    },
    "amendment": {
        "type": "object",
        "required": [
            "contract_type",
            "customer_name",
            "original_agreement_date",
            "amendment_effective_date"
        ],
        "properties": {
            "contract_type": {"type": "string"},
            "amendment_number": {"type": "string"},
            "customer_name": {"type": "string"},
            "original_agreement_date": {"type": "string"},
            "amendment_effective_date": {"type": "string"},
            "previous_contract_value": {"type": "number"},
            "additional_value": {"type": "number"},
            "new_total_value": {"type": "number"},
            "changes_summary": {"type": "array"}
        }
    }
}


def detect_contract_type(text: str) -> str:
    """Detect contract type from document text"""
    text_lower = text.lower()

    if 'master services agreement' in text_lower or 'master subscription agreement' in text_lower:
        return 'master_services_agreement'
    elif 'statement of work' in text_lower or 'sow' in text_lower:
        return 'statement_of_work'
    elif 'amendment' in text_lower:
        return 'amendment'
    else:
        return 'master_services_agreement'


def build_extraction_prompt(contract_text: str, contract_type: str) -> str:
    """Build prompt for GPT-4 extraction"""

    schema = CONTRACT_SCHEMAS.get(contract_type, CONTRACT_SCHEMAS['master_services_agreement'])

    prompt = f"""You are a legal contract analysis AI. Extract structured data from the following contract text.

CONTRACT TYPE: {contract_type.replace('_', ' ').title()}

CONTRACT TEXT:
{contract_text}

INSTRUCTIONS:
1. Extract all relevant fields according to the JSON schema below
2. Use ISO date format (YYYY-MM-DD) for all dates
3. Extract monetary values as numbers (no currency symbols)
4. For arrays, extract all relevant items
5. Identify any risk flags (unusual terms, aggressive clauses, missing critical info)
6. For signatures, extract party name, signatory name, title, and date

JSON SCHEMA:
{json.dumps(schema, indent=2)}

Return ONLY a valid JSON object matching the schema. No additional text or explanation.
"""

    return prompt


def extract_fields_with_gpt4(contract_text: str) -> Dict:
    """Extract contract fields using GPT-4"""

    if not OPENAI_AVAILABLE or not client:
        return {
            "success": False,
            "error": "OpenAI library not available or API key not set"
        }

    try:
        # Detect contract type
        contract_type = detect_contract_type(contract_text)

        # Build prompt
        prompt = build_extraction_prompt(contract_text, contract_type)

        # Call GPT-5
        start_time = datetime.now()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a legal contract analysis expert. Extract structured data from contracts accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=4000,
            response_format={"type": "json_object"}  # Enforce JSON output
        )

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Parse response
        extracted_data = json.loads(response.choices[0].message.content)

        # Add metadata
        # GPT-5 pricing: Input $1.25/1M, Output $10/1M tokens
        input_cost = response.usage.prompt_tokens * 0.00000125
        output_cost = response.usage.completion_tokens * 0.00001
        total_cost = input_cost + output_cost

        result = {
            "success": True,
            "contract_type": contract_type,
            "extracted_data": extracted_data,
            "metadata": {
                "model": "gpt-5",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": round(duration_ms, 2),
                "tokens_used": response.usage.total_tokens,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "cost_estimate_usd": round(total_cost, 6)
            }
        }

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def validate_extracted_data(data: Dict, contract_type: str) -> Dict:
    """Validate extracted data against schema"""

    schema = CONTRACT_SCHEMAS.get(contract_type)
    if not schema:
        return {
            "valid": False,
            "errors": [f"Unknown contract type: {contract_type}"],
            "warnings": [],
            "validation_score": 0
        }

    errors = []
    warnings = []
    missing_required = []

    # Check required fields
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_required.append(field)
            errors.append(f"Required field missing: {field}")

    # Calculate validation score
    total_fields = len(schema.get('properties', {}))
    valid_fields = len([f for f in data.keys() if f in schema.get('properties', {})]) - len(errors)
    validation_score = (valid_fields / total_fields * 100) if total_fields > 0 else 0

    is_valid = len(errors) == 0 and len(missing_required) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "missing_required": missing_required,
        "validation_score": round(validation_score, 1),
        "fields_validated": len(data)
    }


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "openai_available": OPENAI_AVAILABLE,
        "api_key_set": bool(os.getenv('OPENAI_API_KEY'))
    })


@app.route('/api/extract-contract', methods=['POST'])
def extract_contract():
    """
    Extract fields from contract text

    Request body:
    {
        "contract_text": "...",
        "filename": "optional.pdf"
    }

    Response:
    {
        "success": true,
        "contract_type": "master_services_agreement",
        "extracted_data": {...},
        "validation": {...},
        "metadata": {...}
    }
    """

    try:
        # Get request data
        data = request.get_json()

        if not data or 'contract_text' not in data:
            return jsonify({
                "success": False,
                "error": "Missing contract_text in request body"
            }), 400

        contract_text = data['contract_text']
        filename = data.get('filename', 'Unknown')

        # Validate input
        if len(contract_text.strip()) < 100:
            return jsonify({
                "success": False,
                "error": "Contract text too short (minimum 100 characters)"
            }), 400

        # Extract fields using GPT-4
        extraction_result = extract_fields_with_gpt4(contract_text)

        if not extraction_result.get('success'):
            return jsonify(extraction_result), 500

        # Validate extracted data
        validation_result = validate_extracted_data(
            extraction_result['extracted_data'],
            extraction_result['contract_type']
        )

        # Build response
        response = {
            "success": True,
            "filename": filename,
            "contract_type": extraction_result['contract_type'],
            "extracted_data": extraction_result['extracted_data'],
            "validation": validation_result,
            "metadata": extraction_result['metadata']
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@app.route('/api/contract-types', methods=['GET'])
def get_contract_types():
    """Get available contract types and their schemas"""
    return jsonify({
        "contract_types": list(CONTRACT_SCHEMAS.keys()),
        "schemas": CONTRACT_SCHEMAS
    })


if __name__ == '__main__':
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  WARNING: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")

    print("\n" + "=" * 80)
    print("CONTRACT SUMMARIZATION DEMO SERVER")
    print("=" * 80)
    print(f"\nOpenAI Available: {OPENAI_AVAILABLE}")
    print(f"API Key Set: {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"\nStarting server on http://localhost:8000")
    print("\nAPI Endpoints:")
    print("  GET  /api/health              - Health check")
    print("  POST /api/extract-contract    - Extract contract fields")
    print("  GET  /api/contract-types      - Get available contract types")
    print("\nPress Ctrl+C to stop")
    print("=" * 80 + "\n")

    app.run(host='0.0.0.0', port=8000, debug=True)

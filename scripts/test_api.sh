#!/bin/bash
# test_api.sh - Test the deployed Financial AI Assistant API
# Usage: ./scripts/test_api.sh [api-endpoint]

API_ENDPOINT=${1:-$(aws cloudformation describe-stacks \
    --stack-name financial-ai-assistant-prod \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text 2>/dev/null)}

if [ -z "$API_ENDPOINT" ]; then
    echo "❌ No API endpoint found. Pass it as argument or deploy the stack first."
    exit 1
fi

HEALTH_ENDPOINT="${API_ENDPOINT/generate/health}"

echo "============================================================"
echo "Financial AI Assistant - API Tests"
echo "============================================================"
echo "API: $API_ENDPOINT"
echo "============================================================"

# Test 1: Health check
echo -e "\n--- Test 1: Health Check ---"
curl -s "$HEALTH_ENDPOINT" | python3 -m json.tool
echo ""

# Test 2: General financial question
echo -e "\n--- Test 2: General Question ---"
curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "What is a 401(k) retirement plan and how does it work?",
        "use_case": "general",
        "session_id": "test-001"
    }' | python3 -m json.tool
echo ""

# Test 3: Product question
echo -e "\n--- Test 3: Product Question ---"
curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "What types of savings accounts do you offer and what are the interest rates?",
        "use_case": "product_question",
        "session_id": "test-002"
    }' | python3 -m json.tool
echo ""

# Test 4: Compliance question
echo -e "\n--- Test 4: Compliance Question ---"
curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "What are the regulatory requirements for opening a brokerage account?",
        "use_case": "compliance",
        "session_id": "test-003"
    }' | python3 -m json.tool
echo ""

# Test 5: Missing prompt (should return error)
echo -e "\n--- Test 5: Error Case (missing prompt) ---"
curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{
        "use_case": "general"
    }' | python3 -m json.tool
echo ""

echo "============================================================"
echo "✅ Tests complete"
echo "============================================================"

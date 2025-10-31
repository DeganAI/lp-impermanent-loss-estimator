#!/bin/bash

# Test script for LP Impermanent Loss Estimator endpoints
# Tests both local and production deployments

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to local
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================"
echo "LP Impermanent Loss Estimator - Endpoint Tests"
echo "========================================"
echo "Testing against: $BASE_URL"
echo ""

# Function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local expected_code=$4
    local data=$5

    echo -n "Testing $name... "

    if [ "$method" == "GET" ]; then
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    else
        if [ -z "$data" ]; then
            response_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$endpoint")
        else
            response_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    fi

    if [ "$response_code" == "$expected_code" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response_code)"
    else
        echo -e "${RED}FAIL${NC} (Expected HTTP $expected_code, got $response_code)"
    fi
}

# Function to test JSON response
test_json_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo -n "Testing $name... "

    if [ -z "$data" ]; then
        response=$(curl -s -X "$method" "$BASE_URL$endpoint")
    else
        response=$(curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi

    # Check if response is valid JSON
    if echo "$response" | jq empty 2>/dev/null; then
        echo -e "${GREEN}PASS${NC} (Valid JSON)"
        echo "Response preview:"
        echo "$response" | jq -C '.' | head -20
    else
        echo -e "${RED}FAIL${NC} (Invalid JSON)"
        echo "Response: $response"
    fi
    echo ""
}

echo "1. Basic Health Checks"
echo "---------------------"
test_endpoint "Landing Page" "GET" "/" "200"
test_endpoint "Health Check" "GET" "/health" "200"
echo ""

echo "2. AP2 Protocol Endpoints"
echo "-------------------------"
test_endpoint "agent.json (AP2)" "GET" "/.well-known/agent.json" "200"
test_endpoint "x402 metadata" "GET" "/.well-known/x402" "402"
echo ""

echo "3. AP2 Entrypoint Discovery"
echo "---------------------------"
test_endpoint "Entrypoint GET (should return 402)" "GET" "/entrypoints/lp-impermanent-loss-estimator/invoke" "402"
test_endpoint "Entrypoint HEAD (should return 402)" "HEAD" "/entrypoints/lp-impermanent-loss-estimator/invoke" "402"
echo ""

echo "4. JSON Response Tests"
echo "---------------------"
test_json_endpoint "Health Check JSON" "GET" "/health"

test_json_endpoint "agent.json structure" "GET" "/.well-known/agent.json"

test_json_endpoint "x402 metadata structure" "GET" "/.well-known/x402"
echo ""

echo "5. Main API Endpoint Tests"
echo "-------------------------"

# Test with valid Uniswap V3 pool
echo "Test 1: Uniswap V3 WETH/USDC pool (Ethereum)"
test_json_endpoint "LP Estimate - Uniswap V3" "POST" "/lp/estimate" '{
  "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
  "chain": 1,
  "window_hours": 24
}'

# Test with SushiSwap pool
echo "Test 2: SushiSwap WETH/USDC pool (Ethereum)"
test_json_endpoint "LP Estimate - SushiSwap" "POST" "/lp/estimate" '{
  "pool_address": "0x397FF1542f962076d0BFE58eA045FfA2d347ACa0",
  "chain": 1,
  "window_hours": 24
}'

# Test with custom window
echo "Test 3: Custom 7-day window"
test_json_endpoint "LP Estimate - 7 day window" "POST" "/lp/estimate" '{
  "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
  "chain": 1,
  "window_hours": 168
}'

echo ""
echo "6. AP2 Entrypoint Tests"
echo "----------------------"

# Test entrypoint without payment (should work in FREE_MODE)
echo "Test 1: Entrypoint without payment"
test_json_endpoint "Entrypoint POST - no payment" "POST" "/entrypoints/lp-impermanent-loss-estimator/invoke" '{
  "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
  "chain": 1,
  "window_hours": 24
}'

echo ""
echo "7. Validation Tests"
echo "-------------------"

# Test with missing required field
echo "Test 1: Missing chain parameter"
echo -n "Testing validation error handling... "
response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
      "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
      "window_hours": 24
    }' \
    "$BASE_URL/lp/estimate")

if echo "$response" | grep -q "error\|detail"; then
    echo -e "${GREEN}PASS${NC} (Validation error returned)"
else
    echo -e "${RED}FAIL${NC} (No validation error)"
fi

# Test with invalid chain
echo "Test 2: Invalid chain ID"
echo -n "Testing invalid chain handling... "
response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
      "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
      "chain": 99999,
      "window_hours": 24
    }' \
    "$BASE_URL/lp/estimate")

if echo "$response" | grep -q "error\|detail"; then
    echo -e "${GREEN}PASS${NC} (Error returned for invalid chain)"
else
    echo -e "${RED}FAIL${NC} (No error for invalid chain)"
fi

echo ""
echo "========================================"
echo "Test Suite Complete"
echo "========================================"
echo ""
echo -e "${YELLOW}Note:${NC} If testing production (FREE_MODE=false),"
echo "      POST requests without x-payment-txhash header will return 402"
echo ""
echo "To test against production:"
echo "  BASE_URL=https://lp-impermanent-loss-estimator-production.up.railway.app ./test_endpoints.sh"
echo ""

#!/bin/bash
# deploy.sh - Deploy Financial AI Assistant to AWS
# Usage: ./scripts/deploy.sh [region] [environment]

set -e

REGION=${1:-us-east-1}
ENVIRONMENT=${2:-prod}
STACK_NAME="financial-ai-assistant-${ENVIRONMENT}"
TEMPLATE_PATH="cloudformation/template.yaml"

echo "============================================================"
echo "Financial AI Assistant - Deployment"
echo "============================================================"
echo "Region:      $REGION"
echo "Environment: $ENVIRONMENT"
echo "Stack:       $STACK_NAME"
echo "============================================================"

# Validate template
echo -e "\n[1/4] Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body file://$TEMPLATE_PATH \
    --region $REGION > /dev/null
echo "  ✅ Template is valid"

# Deploy stack
echo -e "\n[2/4] Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file $TEMPLATE_PATH \
    --stack-name $STACK_NAME \
    --parameter-overrides Environment=$ENVIRONMENT \
    --region $REGION \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset

echo "  ✅ Stack deployed"

# Get outputs
echo -e "\n[3/4] Retrieving stack outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

HEALTH_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`HealthEndpoint`].OutputValue' \
    --output text)

echo "  API Endpoint:    $API_ENDPOINT"
echo "  Health Endpoint: $HEALTH_ENDPOINT"

# Test health endpoint
echo -e "\n[4/4] Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s $HEALTH_ENDPOINT)
echo "  Response: $HEALTH_RESPONSE"

echo -e "\n============================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "Test the API:"
echo "  curl -X POST $API_ENDPOINT \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\": \"What is a 401k?\", \"use_case\": \"general\", \"session_id\": \"test-1\"}'"
echo ""

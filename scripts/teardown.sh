#!/bin/bash
# teardown.sh - Remove Financial AI Assistant stack from AWS
# Usage: ./scripts/teardown.sh [region] [environment]

set -e

REGION=${1:-us-east-1}
ENVIRONMENT=${2:-prod}
STACK_NAME="financial-ai-assistant-${ENVIRONMENT}"

echo "============================================================"
echo "Financial AI Assistant - Teardown"
echo "============================================================"
echo "Region:      $REGION"
echo "Environment: $ENVIRONMENT"
echo "Stack:       $STACK_NAME"
echo "============================================================"
echo ""
read -p "Are you sure you want to delete this stack? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo -e "\nDeleting stack $STACK_NAME in $REGION..."
aws cloudformation delete-stack \
    --stack-name $STACK_NAME \
    --region $REGION

echo "Waiting for deletion to complete..."
aws cloudformation wait stack-delete-complete \
    --stack-name $STACK_NAME \
    --region $REGION

echo -e "\n✅ Stack deleted successfully."

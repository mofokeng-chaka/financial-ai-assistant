"""
Fallback Model Lambda Handler.

Used when the primary model fails. Uses a simpler, more cost-effective model
with reduced parameters for maximum reliability.

This is the second stage in the Step Functions circuit breaker pattern.
"""

import boto3
import json
import os
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "us.amazon.nova-lite-v1:0")

bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

SYSTEM_PROMPT = """You are a helpful financial services assistant. Provide clear, 
accurate answers about financial products and services. Include disclaimers where appropriate."""


def lambda_handler(event, context):
    """Fallback model handler - uses simpler model with conservative settings.
    
    Expected event format (passed from Step Functions):
    {
        "prompt": "User's question",
        "use_case": "general",
        "is_fallback": true
    }
    """
    start_time = time.time()

    prompt = event.get("prompt", "")
    use_case = event.get("use_case", "general")
    session_id = event.get("session_id", "anonymous")

    if not prompt:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'prompt' field"}),
        }

    logger.info(f"Fallback invocation: model={FALLBACK_MODEL}, use_case={use_case}")

    try:
        response = bedrock_runtime.converse(
            modelId=FALLBACK_MODEL,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[{"text": SYSTEM_PROMPT}],
            inferenceConfig={
                "temperature": 0.2,  # Lower temperature for more predictable output
                "maxTokens": 500,    # Reduced tokens for faster response
            },
        )

        # Extract response text
        output_message = response["output"]["message"]
        response_text = ""
        for block in output_message["content"]:
            if "text" in block:
                response_text += block["text"]

        total_latency = time.time() - start_time

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "response": response_text,
                "metadata": {
                    "model_used": f"FALLBACK:{FALLBACK_MODEL}",
                    "use_case": use_case,
                    "latency_seconds": round(total_latency, 3),
                    "usage": response.get("usage", {}),
                    "session_id": session_id,
                    "region": AWS_REGION,
                    "is_fallback": True,
                },
            }),
        }

    except Exception as e:
        logger.error(f"Fallback model failed: {FALLBACK_MODEL} - {e}")
        # Raise to let Step Functions move to graceful degradation
        raise Exception(f"Fallback model failed: {str(e)}")

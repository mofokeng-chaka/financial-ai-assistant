"""
Lambda Model Abstraction Layer with AppConfig Integration.

This Lambda function:
1. Fetches model selection config from AWS AppConfig
2. Selects the appropriate model based on use case
3. Invokes the model via Bedrock Converse API
4. Returns the response with metadata

Designed to be the primary handler in the Step Functions circuit breaker pattern.
"""

import boto3
import json
import os
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables (set by CloudFormation)
APPCONFIG_APP = os.environ.get("APPCONFIG_APPLICATION", "FinancialAIAssistant")
APPCONFIG_ENV = os.environ.get("APPCONFIG_ENVIRONMENT", "Production")
APPCONFIG_PROFILE = os.environ.get("APPCONFIG_PROFILE", "ModelSelectionStrategy")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1000"))

# Cache config to avoid fetching on every invocation
_config_cache = {"data": None, "timestamp": 0, "ttl": 60}

# Initialize clients outside handler for reuse across invocations
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def get_appconfig():
    """Fetch model selection config from AppConfig with caching.
    
    Uses the AppConfig Data API (StartConfigurationSession + GetLatestConfiguration)
    for efficient polling.
    """
    now = time.time()
    if _config_cache["data"] and (now - _config_cache["timestamp"]) < _config_cache["ttl"]:
        return _config_cache["data"]

    try:
        # Use the AppConfig Data plane client for efficient config retrieval
        appconfig_data = boto3.client("appconfigdata", region_name=AWS_REGION)

        # Start a session
        session_response = appconfig_data.start_configuration_session(
            ApplicationIdentifier=APPCONFIG_APP,
            EnvironmentIdentifier=APPCONFIG_ENV,
            ConfigurationProfileIdentifier=APPCONFIG_PROFILE,
        )
        token = session_response["InitialConfigurationToken"]

        # Get the latest configuration
        config_response = appconfig_data.get_latest_configuration(ConfigurationToken=token)
        content = config_response["Configuration"].read()

        if content:
            config = json.loads(content)
            _config_cache["data"] = config
            _config_cache["timestamp"] = now
            logger.info("AppConfig refreshed successfully")
            return config
        else:
            # No new config, use cached
            logger.info("No new AppConfig data, using cached")
            return _config_cache["data"]

    except Exception as e:
        logger.warning(f"AppConfig fetch failed: {e}. Using default config.")
        # Return a default config if AppConfig is unavailable
        return {
            "primary_model": DEFAULT_MODEL,
            "fallback_models": ["us.anthropic.claude-haiku-4-5-20251001-v1:0", "us.amazon.nova-lite-v1:0"],
            "use_case_models": {},
        }


def select_model(config: dict, use_case: str) -> str:
    """Select the appropriate model based on config and use case."""
    # Check for use-case-specific model mapping
    use_case_models = config.get("use_case_models", {})
    if use_case in use_case_models:
        return use_case_models[use_case]

    # Default to primary model
    return config.get("primary_model", DEFAULT_MODEL)


def invoke_model(model_id: str, prompt: str, system_prompt: str = None) -> dict:
    """Invoke a Bedrock model via the Converse API."""
    messages = [{"role": "user", "content": [{"text": prompt}]}]

    converse_params = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"temperature": 0.3, "maxTokens": MAX_TOKENS},
    }

    # Add system prompt for financial domain context
    if system_prompt:
        converse_params["system"] = [{"text": system_prompt}]

    response = bedrock_runtime.converse(**converse_params)

    # Extract response text
    output_message = response["output"]["message"]
    response_text = ""
    for block in output_message["content"]:
        if "text" in block:
            response_text += block["text"]

    return {
        "text": response_text,
        "usage": response.get("usage", {}),
        "stop_reason": response.get("stopReason", "unknown"),
    }


# Financial domain system prompt
SYSTEM_PROMPT = """You are a knowledgeable financial services assistant for a regulated financial company. 

Guidelines:
- Provide accurate, clear, and helpful information about financial products and services.
- Always include appropriate disclaimers when discussing investments or financial advice.
- Never provide specific investment recommendations or guarantee returns.
- If you don't know something, say so rather than speculating.
- Comply with financial industry regulations by being transparent and fair.
- Protect customer privacy and never ask for sensitive account information.
"""


def lambda_handler(event, context):
    """Main Lambda handler for the model abstraction layer.
    
    Expected event format:
    {
        "prompt": "User's question",
        "use_case": "general|product_question|account_inquiry|compliance",
        "session_id": "optional-session-id",
        "max_tokens": 500  // optional override
    }
    """
    start_time = time.time()

    # Parse input
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))
    prompt = body.get("prompt", "")
    use_case = body.get("use_case", "general")
    session_id = body.get("session_id", "anonymous")
    max_tokens_override = body.get("max_tokens")

    if not prompt:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'prompt' field"}),
        }

    # Get model selection config from AppConfig
    config = get_appconfig()

    # Select model
    model_id = select_model(config, use_case)
    logger.info(f"Selected model: {model_id} for use_case: {use_case}")

    # Override max tokens if provided
    if max_tokens_override:
        global MAX_TOKENS
        MAX_TOKENS = int(max_tokens_override)

    # Invoke model
    try:
        model_response = invoke_model(model_id, prompt, SYSTEM_PROMPT)
    except Exception as e:
        logger.error(f"Model invocation failed: {model_id} - {e}")
        raise  # Let Step Functions handle retry/fallback

    # Build response
    total_latency = time.time() - start_time

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "response": model_response["text"],
            "metadata": {
                "model_used": model_id,
                "use_case": use_case,
                "latency_seconds": round(total_latency, 3),
                "usage": model_response["usage"],
                "session_id": session_id,
                "region": AWS_REGION,
            },
        }),
    }

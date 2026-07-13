"""
Graceful Degradation Lambda Handler.

Last-resort handler when both primary and fallback models are unavailable.
Returns pre-defined responses based on use case to maintain user experience.

This is the final stage in the Step Functions circuit breaker pattern.
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Pre-defined responses for different use cases when AI models are unavailable
DEGRADED_RESPONSES = {
    "general": (
        "Thank you for your question. Our AI assistant is currently experiencing "
        "high demand and is temporarily unavailable. Please try again in a few minutes, "
        "or contact our customer service team at 1-800-555-0100 for immediate assistance. "
        "Our representatives are available Monday-Friday, 8am-8pm EST."
    ),
    "product_question": (
        "I apologize, but I'm unable to access product information at this time. "
        "For detailed information about our financial products, please:\n"
        "• Visit our product page at www.example.com/products\n"
        "• Call our product specialists at 1-800-555-0100\n"
        "• Email us at products@example.com\n\n"
        "We appreciate your patience and will be back online shortly."
    ),
    "account_inquiry": (
        "I'm unable to process account inquiries at the moment due to a temporary "
        "service disruption. For urgent account matters:\n"
        "• Call our secure account line: 1-800-555-0100\n"
        "• Visit your nearest branch\n"
        "• Use our mobile app for basic account functions\n\n"
        "For security, never share your account credentials via email or chat."
    ),
    "compliance": (
        "Our compliance information service is temporarily unavailable. "
        "For regulatory and compliance inquiries, please contact our compliance "
        "department directly at compliance@example.com or call 1-800-555-0101. "
        "All compliance matters will be addressed within one business day."
    ),
    "investment": (
        "Our investment advisory service is temporarily unavailable. "
        "Please note: Past performance does not guarantee future results. "
        "For investment guidance, please speak with a licensed financial advisor "
        "by calling 1-800-555-0100. We'll be back online shortly."
    ),
}


def lambda_handler(event, context):
    """Graceful degradation handler - returns pre-defined responses.
    
    This function never fails - it always returns a helpful response
    directing customers to alternative support channels.
    """
    prompt = event.get("prompt", "")
    use_case = event.get("use_case", "general")
    session_id = event.get("session_id", "anonymous")

    logger.warning(f"Graceful degradation triggered for use_case={use_case}, session={session_id}")

    # Select appropriate degraded response
    response_text = DEGRADED_RESPONSES.get(use_case, DEGRADED_RESPONSES["general"])

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "response": response_text,
            "metadata": {
                "model_used": "DEGRADED_SERVICE",
                "use_case": use_case,
                "session_id": session_id,
                "is_degraded": True,
                "support_phone": "1-800-555-0100",
                "notice": "AI service temporarily unavailable. Pre-defined response served.",
            },
        }),
    }

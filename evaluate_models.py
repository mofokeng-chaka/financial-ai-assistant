"""
Model Evaluation Script for Financial Services AI Assistant.

Evaluates available Bedrock models on financial domain test cases to determine
optimal model selection strategy for AppConfig.

Usage:
    python evaluate_models.py
"""

import boto3
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize Bedrock client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# Models to evaluate (using cross-region inference profiles for active models)
MODELS = [
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "us.amazon.nova-lite-v1:0",
    "us.amazon.nova-micro-v1:0",
]

# Financial domain test cases with ground truth
TEST_CASES = [
    {
        "question": "What is a 401(k) retirement plan?",
        "context": "retirement planning",
        "ground_truth": "A 401(k) is a tax-advantaged retirement savings plan offered by employers that allows employees to contribute a portion of their salary before taxes are taken out.",
    },
    {
        "question": "What is the difference between a Roth IRA and a Traditional IRA?",
        "context": "retirement accounts",
        "ground_truth": "A Roth IRA uses after-tax contributions with tax-free withdrawals in retirement, while a Traditional IRA uses pre-tax contributions with taxable withdrawals in retirement.",
    },
    {
        "question": "How does compound interest work?",
        "context": "savings and investing",
        "ground_truth": "Compound interest is interest calculated on both the initial principal and the accumulated interest from previous periods, causing wealth to grow exponentially over time.",
    },
    {
        "question": "What is dollar-cost averaging?",
        "context": "investment strategy",
        "ground_truth": "Dollar-cost averaging is an investment strategy where you invest a fixed amount at regular intervals regardless of market conditions, reducing the impact of volatility.",
    },
    {
        "question": "What are the risks of investing in mutual funds?",
        "context": "risk assessment",
        "ground_truth": "Mutual fund risks include market risk, interest rate risk, credit risk, liquidity risk, and management risk. The value can fluctuate and you may lose principal.",
    },
    {
        "question": "What is a credit score and why does it matter?",
        "context": "personal finance",
        "ground_truth": "A credit score is a numerical representation of creditworthiness based on credit history. It affects loan approvals, interest rates, and insurance premiums.",
    },
    {
        "question": "Explain the concept of asset allocation.",
        "context": "portfolio management",
        "ground_truth": "Asset allocation is the strategy of dividing investments among different asset classes like stocks, bonds, and cash to balance risk and reward based on goals and risk tolerance.",
    },
    {
        "question": "What is an ETF and how does it differ from a mutual fund?",
        "context": "investment products",
        "ground_truth": "An ETF (Exchange-Traded Fund) trades on exchanges like stocks throughout the day, while mutual funds are priced once daily. ETFs typically have lower fees and greater tax efficiency.",
    },
]


def invoke_model(model_id: str, prompt: str, max_tokens: int = 500) -> dict:
    """Invoke a model via the Converse API and return metrics."""
    start_time = time.time()

    try:
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.3, "maxTokens": max_tokens},
        )

        # Extract text from response
        output_message = response["output"]["message"]
        output = ""
        for block in output_message["content"]:
            if "text" in block:
                output += block["text"]

        latency = time.time() - start_time
        token_count = response.get("usage", {}).get("outputTokens", len(output.split()))

        return {
            "success": True,
            "output": output,
            "latency": latency,
            "token_count": token_count,
            "input_tokens": response.get("usage", {}).get("inputTokens", 0),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency": time.time() - start_time,
        }


def calculate_similarity(output: str, ground_truth: str) -> float:
    """Calculate word-overlap similarity between output and ground truth."""
    output_words = set(output.lower().split())
    truth_words = set(ground_truth.lower().split())

    if not truth_words:
        return 0.0

    common_words = output_words.intersection(truth_words)
    # F1-style score
    precision = len(common_words) / len(output_words) if output_words else 0
    recall = len(common_words) / len(truth_words)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def evaluate_models():
    """Evaluate all models on financial domain test cases."""
    results = []

    for test_case in TEST_CASES:
        prompt = (
            f"You are a financial advisor assistant. Answer the following question "
            f"concisely and accurately.\n\n"
            f"Context: {test_case['context']}\n"
            f"Question: {test_case['question']}\n\n"
            f"Answer:"
        )

        for model_id in MODELS:
            print(f"  Evaluating: {model_id.split('.')[-1][:30]} | Q: {test_case['question'][:50]}...")
            response = invoke_model(model_id, prompt)

            result = {
                "model_id": model_id,
                "question": test_case["question"],
                "latency": response["latency"],
            }

            if response["success"]:
                similarity = calculate_similarity(response["output"], test_case["ground_truth"])
                result.update({
                    "success": True,
                    "output": response["output"][:200],
                    "token_count": response["token_count"],
                    "input_tokens": response.get("input_tokens", 0),
                    "similarity_score": similarity,
                })
            else:
                result.update({
                    "success": False,
                    "error": response["error"],
                    "similarity_score": 0.0,
                })

            results.append(result)

    return results


def create_model_selection_strategy(results: list) -> dict:
    """Create a model selection strategy based on evaluation results."""
    # Aggregate per model
    model_stats = {}
    for r in results:
        mid = r["model_id"]
        if mid not in model_stats:
            model_stats[mid] = {"latencies": [], "similarities": [], "successes": 0, "total": 0}
        model_stats[mid]["total"] += 1
        if r.get("success"):
            model_stats[mid]["successes"] += 1
            model_stats[mid]["latencies"].append(r["latency"])
            model_stats[mid]["similarities"].append(r["similarity_score"])

    # Calculate scores
    model_scores = []
    for mid, stats in model_stats.items():
        if not stats["latencies"]:
            continue
        avg_latency = sum(stats["latencies"]) / len(stats["latencies"])
        avg_similarity = sum(stats["similarities"]) / len(stats["similarities"])
        success_rate = stats["successes"] / stats["total"]

        model_scores.append({
            "model_id": mid,
            "avg_latency": round(avg_latency, 3),
            "avg_similarity": round(avg_similarity, 3),
            "success_rate": round(success_rate, 3),
        })

    # Normalize and calculate weighted score
    if not model_scores:
        return {"error": "No successful evaluations"}

    max_latency = max(m["avg_latency"] for m in model_scores)
    for m in model_scores:
        latency_score = 1 - (m["avg_latency"] / max_latency) if max_latency > 0 else 0
        m["overall_score"] = round(
            0.5 * m["avg_similarity"] + 0.3 * latency_score + 0.2 * m["success_rate"], 3
        )

    # Sort by overall score
    model_scores.sort(key=lambda x: x["overall_score"], reverse=True)

    strategy = {
        "primary_model": model_scores[0]["model_id"],
        "fallback_models": [m["model_id"] for m in model_scores[1:]],
        "use_case_models": {
            "general": model_scores[0]["model_id"],
            "product_question": model_scores[0]["model_id"],
            "account_inquiry": model_scores[0]["model_id"],
            "compliance": model_scores[0]["model_id"],
        },
        "model_scores": model_scores,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    return strategy


if __name__ == "__main__":
    print("=" * 60)
    print("Financial AI Assistant - Model Evaluation")
    print("=" * 60)
    print(f"\nModels: {len(MODELS)}")
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Total evaluations: {len(MODELS) * len(TEST_CASES)}\n")

    results = evaluate_models()

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    strategy = create_model_selection_strategy(results)

    if "error" not in strategy:
        print(f"\n{'Model':<50} {'Latency':>8} {'Similarity':>11} {'Score':>7}")
        print("-" * 80)
        for m in strategy["model_scores"]:
            print(f"{m['model_id']:<50} {m['avg_latency']:>7.2f}s {m['avg_similarity']:>10.3f} {m['overall_score']:>7.3f}")

        print(f"\n✅ Primary model: {strategy['primary_model']}")
        print(f"   Fallback models: {strategy['fallback_models']}")

        # Save strategy for AppConfig
        output_path = os.path.join(os.path.dirname(__file__), "config", "model_selection_strategy.json")
        with open(output_path, "w") as f:
            json.dump(strategy, f, indent=2)
        print(f"\n📁 Strategy saved to: {output_path}")
    else:
        print(f"\n❌ Evaluation failed: {strategy['error']}")

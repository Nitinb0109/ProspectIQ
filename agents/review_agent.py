
import os
import json
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found.")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=API_KEY,
    temperature=0.1
)


def review_email(
    email_data,
    analyzed_data,
    product_or_service,
    value_proposition
):
    signals = analyzed_data.get("signals", [])

    valid_urls = {
        signal.get("source_url")
        for signal in signals
        if signal.get("source_url")
    }

    # Select only the research signal used in the email.
    source_url = email_data.get("source_url", "")

    selected_signal = next(
    (
        signal for signal in signals
        if signal.get("source_url") == source_url
    ),
    None
    )

# Reject invalid sources without making another LLM call.
    if not selected_signal:
        return {
        "approved": False,
        "quality_score": 0,
        "factual_accuracy": "Fail",
        "product_accuracy": "Fail",
        "personalization": "Fail",
        "professionalism": "Fail",
        "issues": ["No matching research source was found."],
        "suggestions": ["Regenerate the email using a verified research signal."],
        "review_summary": "Review rejected because the supporting source is invalid."
        }


    prompt = f"""
You are a strict B2B sales email quality reviewer.

Review the generated email using the supplied research
and sender information.

GENERATED EMAIL:
{json.dumps(email_data, indent=2)}

SELECTED RESEARCH SIGNAL:
{json.dumps(selected_signal, indent=2)}

SENDER PRODUCT:
{product_or_service}

SENDER VALUE PROPOSITION:
{value_proposition}

CHECK THE FOLLOWING:

1. Factual accuracy:
   Are all claims about the prospect and company supported
   by the supplied research?

2. Product accuracy:
   Does the email claim product capabilities that the
   sender has not explicitly provided?

3. Personalization:
   Is the email genuinely connected to a relevant research signal?

4. Relevance:
   Does the proposed opportunity logically connect the
   prospect's signal with the sender's offering?

5. Professionalism:
   Is the email concise, respectful and professional?

6. Source validity:
   Is the personalization supported by a supplied source URL?

STRICT RULES:
- The sender's product description and value proposition are
  the only evidence of product capabilities.
- Do not assume integrations, partnerships or technical features.
- Research signals do not prove anything about the sender's product.
- Identify specific unsupported claims.
- Do not approve emails with serious factual or product problems.
- Do not invent facts while suggesting improvements.

SCORING RUBRIC:
Return an INTEGER quality_score between 0 and 100.

Use these weights:
- Factual accuracy: 30 points
- Product accuracy: 25 points
- Personalization: 20 points
- Relevance: 15 points
- Professionalism: 10 points

A serious factual or product accuracy failure should
significantly reduce the score.

APPROVAL:
Approve only if all critical factual and product claims
are supported and the email is relevant and professional.

Return ONLY valid JSON:

{{
    "approved": false,
    "quality_score": 0,
    "factual_accuracy": "Pass or Fail",
    "product_accuracy": "Pass or Fail",
    "personalization": "Pass or Fail",
    "professionalism": "Pass or Fail",
    "issues": [],
    "suggestions": [],
    "review_summary": "Short explanation"
}}
"""

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )

    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content)

    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Groq returned invalid JSON: {content}"
        ) from error

    required_fields = [
        "approved",
        "quality_score",
        "factual_accuracy",
        "product_accuracy",
        "personalization",
        "professionalism",
        "issues",
        "suggestions",
        "review_summary"
    ]

    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing review field: {field}")

    # Ensure the score is an integer between 0 and 100.
    try:
        score = float(result["quality_score"])
        if not 0 <= score <= 100:
            raise ValueError("Score is outside the 0-100 range.")
        result["quality_score"] = round(score)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid review quality score.") from error

    # Check whether the email has a genuine supporting source.
    email_body = email_data.get("email_body", "")

    source_is_valid = (
        bool(source_url)
        and source_url in valid_urls
    )

    if email_body and not source_is_valid:
        result.setdefault("issues", []).append(
            "Email is missing a valid supporting research source."
        )

    # Enforce critical approval conditions in Python.
    critical_checks_pass = (
        result["factual_accuracy"] == "Pass"
        and result["product_accuracy"] == "Pass"
        and result["personalization"] == "Pass"
        and result["professionalism"] == "Pass"
        and source_is_valid
        and bool(email_body.strip())
    )

    result["approved"] = (
        result["approved"] is True
        and critical_checks_pass
        and result["quality_score"] >= 70
    )

    return result


def review_agent(state):
    """
    Review the generated outreach email
    for accuracy, relevance and quality.
    """

    print("\n--- REVIEW AGENT STARTED ---")

    review_result = review_email(
        email_data=state["email_data"],
        analyzed_data=state["analyzed_data"],
        product_or_service=state["product_or_service"],
        value_proposition=state["value_proposition"]
    )

    print("--- REVIEW AGENT COMPLETED ---")

    return {
        "review_result": review_result
    }

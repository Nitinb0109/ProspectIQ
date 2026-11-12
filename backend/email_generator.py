import os
import json
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=API_KEY,
    temperature=0.4
)


def generate_email(
    analyzed_data,
    sender_company,
    product_or_service,
    value_proposition
):
    prospect = analyzed_data["prospect"]
    company = analyzed_data["company"]
    signals = analyzed_data["signals"]

    prompt = f"""
You are an expert B2B sales email copywriter.

Write a personalized, concise and professional cold outreach email.

PROSPECT:
Name: {prospect}

Target Company:
{company}

SENDER INFORMATION:
Sender Company: {sender_company}
Product/Service: {product_or_service}
Value Proposition: {value_proposition}

RESEARCH SIGNALS:
{json.dumps(signals, indent=2)}

INSTRUCTIONS:
1. Personalize the email using the strongest relevant research signal.
2. Explain why the signal creates a relevant business conversation.
3. Connect the signal naturally to the sender's product or service.
4. Do not invent facts, achievements, relationships or customer results.
5. Do not claim that the prospect has a problem unless the sources support it.
6. Keep the email between 100 and 150 words.
7. Use a professional, natural and conversational tone.
8. Avoid generic openings such as "I hope this email finds you well".
9. Include a simple, low-pressure call to action.
10. Do not pretend the sender knows the prospect personally.
11. Do not include unsupported claims.

Return ONLY valid JSON:

{{
    "subject": "Email subject",
    "email_body": "Complete email body",
    "personalization_signal": "Signal used",
    "source_url": "URL supporting the personalization",
    "reasoning": "Why this email is relevant"
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

    return result
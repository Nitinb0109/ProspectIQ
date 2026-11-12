
import os
import json
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=API_KEY,
    temperature=0.1
)


def qualify_companies(extraction_data, campaign, research_data=None):

    companies = extraction_data.get("companies", [])

    if not companies:
        return {
            "total_companies": 0,
            "qualified_leads": [],
            "needs_research": [],
            "rejected_leads": []
        }

    # 1. Create a lookup for additional company research
    research_lookup = {}

    if research_data:
        for company in research_data.get("companies", []):
            name = company.get("company_name", "").strip().lower()

            if name:
                research_lookup[name] = company

    # 2. Combine original evidence with targeted research
    compact_companies = []

    for company in companies:

        name = company.get("company_name", "")
        research = research_lookup.get(name.strip().lower(), {})

        research_sources = []

        for source in research.get("research_sources", [])[:5]:
            research_sources.append({
                "title": source.get("title"),
                "url": source.get("url"),
                "content": source.get("content", "")[:500]
            })

        compact_companies.append({
            "company_name": name,
            "industry": company.get("industry"),
            "website": company.get("website"),
            "original_evidence": company.get("evidence"),
            "original_buying_signal": company.get("buying_signal"),
            "original_fit_reason": company.get("fit_reason"),
            "source_urls": company.get("source_urls", []),
            "additional_research": research_sources
        })

    # 3. Ask the LLM to qualify each company
    prompt = f"""
You are a strict B2B lead qualification analyst.

CAMPAIGN:
{json.dumps(campaign)}

COMPANIES:
{json.dumps(compact_companies)}

Evaluate every company independently.

SCORING:

1. ICP FIT (0-100)
Evaluate whether available evidence supports the target
industry, location, company size and ideal customer profile.

2. PRODUCT FIT (0-100)
Evaluate whether evidence supports a business problem
that the seller's product could reasonably solve.

3. BUYING INTENT (0-100)
Look for specific evidence-backed signals such as:
- Relevant job openings
- Technology investment
- Publicly announced automation initiatives
- Explicit demand for a relevant solution
- Relevant business expansion

4. OVERALL SCORE (0-100)
Calculate using:
40% ICP fit
35% Product fit
25% Buying intent

IMPORTANT RULES:

- Never invent employee count, revenue or technology usage.
- Never assume a company has 50-500 employees.
- If employee count is unknown, mark it as unknown.
- If employee count exceeds the campaign's maximum,
  the company cannot be Qualified.
- A company directory listing is not a buying signal.
- A high Glassdoor rating is not a buying signal.
- General hiring or business expansion alone does not
  prove demand for the seller's product.
- Do not confuse competitors with potential customers.
- Mark competitor risk when the company sells a similar product.
- Missing information must be marked unknown.
- Distinguish verified facts from assumptions.
- If there is no evidence of buying intent, assign 0.
- Do not qualify a company solely because its industry matches.
- Use only the supplied evidence and research sources.
- Include source URLs supporting your conclusions.

STATUS RULES:

Qualified:
Strong ICP fit and product fit, with credible evidence
of a relevant business need.

Needs Research:
Potential fit, but important information is missing.

Rejected:
Clearly outside the ICP, unsuitable product fit,
or a direct competitor.

Return ONLY valid JSON in this format:

{{
    "results": [
        {{
            "company_name": "Company name",
            "icp_fit_score": 0,
            "product_fit_score": 0,
            "buying_intent_score": 0,
            "overall_score": 0,
            "employee_count": "Unknown",
            "verified_facts": [],
            "unknown_information": [],
            "buying_signals": [],
            "competitor_risk": "Low, Medium or High",
            "rejection_reasons": [],
            "evidence_urls": [],
            "qualification_status": "Qualified, Needs Research or Rejected",
            "reasoning": "Short explanation"
        }}
    ]
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

    content = content.strip()

    # Remove Markdown code fences if the model returns them
    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(r"\s*```$", "", content)

    try:
        result = json.loads(content)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid qualification JSON: {content}"
        ) from error

    # 4. Separate companies by qualification status
    qualified = []
    rejected = []
    needs_research = []

    for company in result.get("results", []):

        status = company.get("qualification_status")

        if status == "Qualified":
            qualified.append(company)

        elif status == "Rejected":
            rejected.append(company)

        else:
            needs_research.append(company)

    return {
        "total_companies": len(result.get("results", [])),
        "qualified_leads": qualified,
        "needs_research": needs_research,
        "rejected_leads": rejected
    }

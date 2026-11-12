
import os
import json

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

if not API_KEY:
    raise ValueError("TAVILY_API_KEY not found in .env file")

tavily = TavilyClient(api_key=API_KEY)


def research_company(company):

    name = company["company_name"]

    print(f"\nResearching: {name}")

    query = f"""
    {name} company official website business operations
    recent news hiring expansion funding technology adoption
    AI automation workflow challenges company size employees
    """

    response = tavily.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_answer=False
    )

    sources = []

    for result in response.get("results", []):

        sources.append({
            "title": result.get("title"),
            "url": result.get("url"),
            "content": result.get("content", "")[:700],
            "relevance_score": result.get("score")
        })

    return {
        "company_name": name,
        "industry": company.get("industry"),
        "original_evidence": company.get("evidence"),
        "research_sources": sources,
        "total_sources": len(sources)
    }


def research_companies(qualification_data):

    companies = qualification_data.get("needs_research", [])

    results = []

    for company in companies:

        research = research_company(company)

        results.append(research)

    return {
        "total_companies_researched": len(results),
        "companies": results
    }

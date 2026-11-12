
import os
import json
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

if not API_KEY:
    raise ValueError("TAVILY_API_KEY not found. Check your .env file.")

tavily = TavilyClient(api_key=API_KEY)


def normalize_url(url):
    """Normalize URLs to avoid duplicate search results."""

    try:
        parsed = urlsplit(url)

        hostname = (parsed.hostname or "").lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        path = parsed.path.rstrip("/")

        return urlunsplit((
            parsed.scheme.lower(),
            hostname,
            path,
            "",
            ""
        ))

    except Exception:
        return url.lower().rstrip("/")


def generate_discovery_queries(
    product,
    target_industry,
    target_location,
    ideal_customer
):
    """Generate diverse searches for potential companies."""

    industry = target_industry
    location = target_location
    icp = ideal_customer

    queries = [
        {
            "category": "company_directories",
            "query": (
                f"list of {industry} companies in {location} "
                f"{icp}"
            )
        },
        {
            "category": "b2b_companies",
            "query": (
                f"B2B {industry} companies headquartered in "
                f"{location} {icp}"
            )
        },
        {
            "category": "funded_startups",
            "query": (
                f"{industry} startups in {location} "
                f"recently raised Series A or Series B funding"
            )
        },
        {
            "category": "fast_growing_companies",
            "query": (
                f"fast growing {industry} companies in "
                f"{location} {icp}"
            )
        },
        {
            "category": "hiring_signals",
            "query": (
                f"{industry} companies in {location} "
                f"hiring operations automation AI data "
                f"or engineering employees"
            )
        },
        {
            "category": "business_expansion",
            "query": (
                f"{industry} companies in {location} "
                f"announcing business expansion new markets "
                f"or operational growth"
            )
        },
        {
            "category": "technology_adoption",
            "query": (
                f"{industry} companies in {location} "
                f"investing in new technology digital "
                f"transformation or business software"
            )
        },
        {
            "category": "ai_initiatives",
            "query": (
                f"{industry} companies in {location} "
                f"announcing AI adoption automation "
                f"or AI transformation initiatives"
            )
        },
        {
            "category": "employee_size",
            "query": (
                f"{industry} companies in {location} "
                f"with {icp} employee count"
            )
        },
        {
            "category": "industry_lists",
            "query": (
                f"top private and independent {industry} "
                f"companies in {location}"
            )
        },
        {
            "category": "company_news",
            "query": (
                f"{industry} companies in {location} "
                f"recent company announcements product "
                f"launches partnerships and growth"
            )
        },
        {
            "category": "product_relevance",
            "query": (
                f"companies in {industry} in {location} "
                f"using or evaluating solutions related to "
                f"{product}"
            )
        }
    ]

    return queries


def discover_prospects(
    product,
    target_industry,
    target_location,
    ideal_customer
):
    """
    Discover potential companies using multiple
    public web search strategies.
    """

    queries = generate_discovery_queries(
        product,
        target_industry,
        target_location,
        ideal_customer
    )

    all_results = []
    seen_urls = set()

    successful_queries = 0
    failed_queries = []

    print(f"Starting discovery with {len(queries)} queries...")

    for index, search_item in enumerate(queries, start=1):

        query = search_item["query"]
        category = search_item["category"]

        print(
            f"\n[{index}/{len(queries)}] "
            f"Searching: {category}"
        )

        try:
            response = tavily.search(
                query=query,
                topic="general",
                search_depth="advanced",
                max_results=6
            )

            successful_queries += 1

            for item in response.get("results", []):

                url = item.get("url")

                if not url:
                    continue

                normalized = normalize_url(url)

                if normalized in seen_urls:
                    continue

                seen_urls.add(normalized)

                all_results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "normalized_url": normalized,
                    "content": item.get("content", ""),
                    "score": item.get("score"),
                    "search_query": query,
                    "category": category
                })

        except Exception as error:

            print(f"Search failed: {category}")
            print(f"Reason: {error}")

            failed_queries.append({
                "category": category,
                "query": query,
                "error": str(error)
            })

    result = {
        "campaign": {
            "product": product,
            "target_industry": target_industry,
            "target_location": target_location,
            "ideal_customer": ideal_customer
        },
        "total_queries": len(queries),
        "successful_queries": successful_queries,
        "failed_queries": failed_queries,
        "total_sources": len(all_results),
        "sources": all_results
    }

    print("\nDISCOVERY SUMMARY")
    print("Queries:", len(queries))
    print("Successful queries:", successful_queries)
    print("Failed queries:", len(failed_queries))
    print("Unique sources:", len(all_results))

    return result

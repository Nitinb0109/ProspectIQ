
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

API_KEY = os.getenv("TAVILY_API_KEY")

if not API_KEY:
    raise ValueError("TAVILY_API_KEY not found. Check your .env file.")

tavily = TavilyClient(api_key=API_KEY)


def research_prospect(name, role, company, website=None):
    """
    Search for public, business-relevant information about a prospect
    and their company.
    """

    searches = [
        {
            "query": f"{company} latest company news announcements",
            "topic": "news"
        },
        {
            "query": f"{company} funding product launches business growth",
            "topic": "news"
        },
        {
            "query": f"{company} careers hiring open positions",
            "topic": "general"
        },
        {
            "query": f"{name} {role} {company} public interview insights",
            "topic": "news"
        }
    ]

    if website:
        searches.append({
            "query": f"site:{website} {company} company updates products",
            "topic": "general"
        })

    all_results = []
    seen_urls = set()

    for search in searches:
        try:
            response = tavily.search(
                query=search["query"],
                topic=search["topic"],
                max_results=5
            )

            for result in response.get("results", []):
                url = result.get("url")

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                all_results.append({
                    "title": result.get("title", ""),
                    "url": url,
                    "content": result.get("content", ""),
                    "published_date": result.get("published_date"),
                    "search_query": search["query"]
                })

        except Exception as error:
            print(f"Search failed for '{search['query']}': {error}")

    return {
        "prospect": {
            "name": name,
            "role": role,
            "company": company,
            "website": website
        },
        "total_sources": len(all_results),
        "sources": all_results
    }

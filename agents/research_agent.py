
from backend.research import research_prospect


def research_agent(state):
    """
    Research the given prospect and their company.
    """

    print("\n--- RESEARCH AGENT STARTED ---")

    prospect_name = state["prospect_name"]
    designation = state["designation"]
    company = state["company"]
    company_website = state.get("company_website")

    research_data = research_prospect(
        name=prospect_name,
        role=designation,
        company=company,
        website=company_website
    )

    print("--- RESEARCH AGENT COMPLETED ---")

    return {
        "research_data": research_data
    }

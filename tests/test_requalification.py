
import json

from agents.qualification_agent import qualify_companies


def main():

    with open("data/extracted_companies.json", "r", encoding="utf-8") as f:
        extraction_data = json.load(f)

    with open("data/company_research_results.json", "r", encoding="utf-8") as f:
        research_data = json.load(f)

    campaign = {
        "product": "AI workflow automation platform",
        "target_industry": "SaaS",
        "target_location": "United States",
        "ideal_customer": "Companies with 50 to 500 employees"
    }

    result = qualify_companies(
        extraction_data,
        campaign,
        research_data
    )

    print(json.dumps(result, indent=4))

    with open("data/requalified_leads.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print("\nResults saved to data/requalified_leads.json")


if __name__ == "__main__":
    main()

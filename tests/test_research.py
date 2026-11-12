

from agents.research_agent import research_agent


test_state = {
    "prospect_name": "Satya Nadella",
    "designation": "CEO",
    "company": "Microsoft",
    "company_website": "https://www.microsoft.com"
}

result = research_agent(test_state)

print("\nResearch result:")
print("Prospect:", result["research_data"]["prospect"])
print("Total sources:", result["research_data"]["total_sources"])

for source in result["research_data"]["sources"][:3]:
    print("\nTitle:", source.get("title"))
    print("URL:", source.get("url"))

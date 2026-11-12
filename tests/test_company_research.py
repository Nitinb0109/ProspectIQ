
import json

from backend.company_research import research_companies

with open(
    "data/qualified_leads.json",
    "r",
    encoding="utf-8"
) as file:
    qualification_data = json.load(file)

print("Starting targeted company research...")

result = research_companies(qualification_data)

print("\nCOMPANY RESEARCH COMPLETED")
print("Companies researched:", result["total_companies_researched"])

for company in result["companies"]:

    print("\n------------------------------")
    print("Company:", company["company_name"])
    print("Sources found:", company["total_sources"])

    for source in company["research_sources"]:
        print("\nTitle:", source["title"])
        print("URL:", source["url"])
        print("Evidence:", source["content"][:250])

with open(
    "data/company_research_results.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4)

print("\nSaved to data/company_research_results.json")

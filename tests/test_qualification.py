
import json

from agents.qualification_agent import qualify_companies

with open("data/extracted_companies.json", "r", encoding="utf-8") as file:
    extraction_data = json.load(file)

campaign = {
    "product": "AI workflow automation platform",
    "target_industry": "SaaS",
    "target_location": "United States",
    "ideal_customer": "Companies with 50 to 500 employees"
}

print("Starting lead qualification...")

result = qualify_companies(extraction_data, campaign)

print("\nQUALIFICATION COMPLETED")

print("\nQualified leads:", len(result["qualified_leads"]))
print("Needs research:", len(result["needs_research"]))
print("Rejected leads:", len(result["rejected_leads"]))

for company in (
    result["qualified_leads"]
    + result["needs_research"]
    + result["rejected_leads"]
):
    print("\n------------------------------")
    print("Company:", company["company_name"])
    print("ICP Fit:", company["icp_fit_score"])
    print("Product Fit:", company["product_fit_score"])
    print("Buying Intent:", company["buying_intent_score"])
    print("Overall Score:", company["overall_score"])
    print("Status:", company["qualification_status"])
    print("Reason:", company["reasoning"])

with open(
    "data/qualified_leads.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4)

print("\nSaved to data/qualified_leads.json")

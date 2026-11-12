
import json

from agents.discovery_agent import extract_companies

with open(
    "data/discovery_results.json",
    "r",
    encoding="utf-8"
) as file:
    discovery_data = json.load(file)

print("Extracting potential customer companies...")

result = extract_companies(discovery_data)

print("\nCOMPANY EXTRACTION COMPLETED")
print("Total candidates:", result["total_candidates"])

for i, company in enumerate(result["companies"], start=1):

    print(f"\n--- Company {i} ---")
    print("Name:", company["company_name"])
    print("Website:", company["website"])
    print("Industry:", company["industry"])
    print("Evidence:", company["evidence"])
    print("Buying Signal:", company["buying_signal"])
    print("Fit Reason:", company["fit_reason"])
    print("Confidence:", company["confidence"])
    print("Sources:", company["source_urls"])

print("\nResearch Summary:")
print(result["research_summary"])

print("\nLimitations:")
for item in result["limitations"]:
    print("-", item)

with open(
    "data/extracted_companies.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nSaved to data/extracted_companies.json")

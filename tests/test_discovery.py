
import json

from backend.prospect_discovery import discover_prospects

print("Starting prospect discovery...")

result = discover_prospects(
    product="AI workflow automation platform",
    target_industry="SaaS",
    target_location="United States",
    ideal_customer="Companies with 50 to 500 employees"
)

print("\nPROSPECT DISCOVERY COMPLETED")
print("Total sources found:", result["total_sources"])

for i, source in enumerate(result["sources"], start=1):
    print(f"\n--- Source {i} ---")
    print("Title:", source["title"])
    print("URL:", source["url"])
    print("Content:", source["content"][:300])

with open(
    "data/discovery_results.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nSaved to data/discovery_results.json")

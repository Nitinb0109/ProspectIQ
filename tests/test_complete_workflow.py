
from workflow.graph import run_prospect_workflow

prospect_data = {
    "prospect_name": "Satya Nadella",
    "designation": "CEO",
    "company": "Microsoft",
    "company_website": "microsoft.com",

    "sender_company": "Your Company",
    "product_or_service": "AI-powered analytics platform",
    "value_proposition": (
        "Helps enterprises analyze business data "
        "and improve operational decision-making."
    )
}

result = run_prospect_workflow(prospect_data)

print("\n--- FINAL RESULT ---")
print("Research sources:", result["research_data"]["total_sources"])
print("Signals:", len(result["analyzed_data"]["signals"]))
print("\nGenerated email:")
print(result["email_data"])
print("\nReview:")
print(result["review_result"])

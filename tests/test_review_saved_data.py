
import json

from agents.review_agent import review_email


# Load previously generated research signals
with open(
    "data/analyzed_signals.json",
    "r",
    encoding="utf-8"
) as file:
    analyzed_data = json.load(file)


# Load previously generated email
with open(
    "data/generated_email.json",
    "r",
    encoding="utf-8"
) as file:
    email_data = json.load(file)


# Run only the Review Agent
result = review_email(
    email_data=email_data,
    analyzed_data=analyzed_data,
    product_or_service="AI-powered analytics platform",
    value_proposition=(
        "Helps enterprises analyze business data, "
        "identify meaningful insights, understand "
        "operational trends, and make better data-driven decisions."
    )
)


print("\nREVIEW TEST COMPLETED")
print(json.dumps(result, indent=4, ensure_ascii=False))


# Save review result
with open(
    "data/review_result.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nSaved to data/review_result.json")

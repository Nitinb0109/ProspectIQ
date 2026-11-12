
import json

from agents.review_agent import review_email

with open("data/generated_email.json", "r", encoding="utf-8") as file:
    email_data = json.load(file)

with open("data/analyzed_signals.json", "r", encoding="utf-8") as file:
    analyzed_data = json.load(file)

print("Sending email for quality review...")

result = review_email(
    email_data=email_data,
    analyzed_data=analyzed_data,
    product_or_service="AI workflow automation platform",
    value_proposition=(
        "Helps enterprises automate repetitive workflows "
        "and improve operational efficiency."
    )
)

print("\nEMAIL REVIEW COMPLETED")
print("Approved:", result["approved"])
print("Quality Score:", result["quality_score"])
print("Factual Accuracy:", result["factual_accuracy"])
print("Product Accuracy:", result["product_accuracy"])
print("Personalization:", result["personalization"])
print("Professionalism:", result["professionalism"])

print("\nIssues:")
for issue in result["issues"]:
    print("-", issue)

print("\nSuggestions:")
for suggestion in result["suggestions"]:
    print("-", suggestion)

print("\nReview Summary:")
print(result["review_summary"])

with open("data/review_result.json", "w", encoding="utf-8") as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nSaved to data/review_result.json")

import json

from backend.email_generator import generate_email

with open(
    "data/analyzed_signals.json",
    "r",
    encoding="utf-8"
) as file:
    analyzed_data = json.load(file)


result = generate_email(
    analyzed_data=analyzed_data,
    sender_company="Your Company",
    product_or_service="AI workflow automation platform",
    value_proposition=(
        "Helps enterprises automate repetitive workflows "
        "and improve operational efficiency."
    )
)

print("\nEMAIL GENERATION COMPLETED")

print("\nSubject:")
print(result["subject"])

print("\nEmail Body:")
print(result["email_body"])

print("\nPersonalization Signal:")
print(result["personalization_signal"])

print("\nSource:")
print(result["source_url"])

print("\nReasoning:")
print(result["reasoning"])

with open(
    "data/generated_email.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nSaved to data/generated_email.json")

from backend.email_generator import generate_email


def writer_agent(state):
    """
    Generate a personalised outreach email
    using the analyzed prospect signals.
    """

    print("\n--- WRITER AGENT STARTED ---")

    analyzed_data = state["analyzed_data"]

    email_data = generate_email(
        analyzed_data=analyzed_data,
        sender_company=state["sender_company"],
        product_or_service=state["product_or_service"],
        value_proposition=state["value_proposition"]
    )

    print("--- WRITER AGENT COMPLETED ---")

    return {
        "email_data": email_data
    }

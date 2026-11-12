
from agents.research_agent import research_agent
from agents.analysis_agent import analysis_agent
from agents.writer_agent import writer_agent
from agents.review_agent import review_agent

state = {
    "prospect_name": "Satya Nadella",
    "designation": "CEO",
    "company": "Microsoft",
    "company_website": "https://www.microsoft.com",
    "sender_company": "Your Company",
    "product_or_service": "AI-powered analytics platform",
    "value_proposition": "Help businesses make better decisions using AI."
}

state.update(research_agent(state))
state.update(analysis_agent(state))
state.update(writer_agent(state))

result = review_agent(state)

print("\nReview result:")
print(result["review_result"])

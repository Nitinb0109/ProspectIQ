
from agents.research_agent import research_agent
from agents.analysis_agent import analysis_agent

state = {
    "prospect_name": "Satya Nadella",
    "designation": "CEO",
    "company": "Microsoft",
    "company_website": "https://www.microsoft.com"
}

# Step 1: Research
research_result = research_agent(state)
state.update(research_result)

# Step 2: Analyze signals
analysis_result = analysis_agent(state)

print("\nAnalyzed signals:")
print(analysis_result["analyzed_data"])


from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END

from agents.research_agent import research_agent
from agents.analysis_agent import analysis_agent
from agents.writer_agent import writer_agent
from agents.review_agent import review_agent


class ProspectState(TypedDict, total=False):
    prospect_name: str
    designation: str
    company: str
    company_website: Optional[str]

    sender_company: str
    product_or_service: str
    value_proposition: str

    research_data: dict
    analyzed_data: dict
    email_data: dict
    review_result: dict


def build_workflow():

    workflow = StateGraph(ProspectState)

    workflow.add_node("research", research_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("review", review_agent)

    workflow.set_entry_point("research")

    workflow.add_edge("research", "analysis")
    workflow.add_edge("analysis", "writer")
    workflow.add_edge("writer", "review")
    workflow.add_edge("review", END)

    return workflow.compile()


prospect_workflow = build_workflow()


def run_prospect_workflow(prospect_data: dict):
    result = prospect_workflow.invoke(prospect_data)
    return result

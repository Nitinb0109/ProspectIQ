
from backend.signal_analyzer import analyze_signals


def analysis_agent(state):
    """
    Identify and evaluate relevant business signals
    from the prospect research results.
    """

    print("\n--- ANALYSIS AGENT STARTED ---")

    research_data = state["research_data"]

    analyzed_data = analyze_signals(research_data)

    print("--- ANALYSIS AGENT COMPLETED ---")

    return {
        "analyzed_data": analyzed_data
    }

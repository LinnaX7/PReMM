from langgraph.graph import StateGraph, END, START
from basic_framework.repair_edge import *
from basic_framework.repair_nodes import *


def get_repair_agent():
    repair_graph = StateGraph(AgentState)
    # Add nodes
    repair_graph.add_node(AgentNodeEnum.FAULT_ANALYZER, fault_analyzer)
    repair_graph.add_node(AgentNodeEnum.REPAIRER, repairer)
    repair_graph.add_node(AgentNodeEnum.MODIFY_AND_COMPILE_CODES, modify_and_compile_codes)
    repair_graph.add_node(AgentNodeEnum.RECOVER_CODES, recover_codes)

    repair_graph.add_conditional_edges(
        START, start_node_choose
    )

    repair_graph.add_conditional_edges(
        AgentNodeEnum.FAULT_ANALYZER,
        fault_analysis_choose
    )

    repair_graph.add_conditional_edges(
        AgentNodeEnum.MODIFY_AND_COMPILE_CODES,
        compile_codes_choose
    )

    repair_graph.add_conditional_edges(
        AgentNodeEnum.RECOVER_CODES,
        recover_choose
    )

    repair_graph.add_conditional_edges(
        AgentNodeEnum.REPAIRER,
        repair_choose
    )

    repair_agent = repair_graph.compile()
    return repair_agent

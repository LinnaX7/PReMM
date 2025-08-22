from langgraph.graph import StateGraph, END
from basic_framework.main_nodes import *
from basic_framework.main_edge import *
from basic_framework.all_enum import MAgentNodeEnum

main_graph = StateGraph(MAgentState)
    # Add nodes
main_graph.add_node(MAgentNodeEnum.PREPROCESSOR, preprocessor)
main_graph.add_node(MAgentNodeEnum.MULTY_REPAIRER, multi_repairer)
main_graph.add_node(MAgentNodeEnum.COMBINE_AND_TEST, combine_and_test)
main_graph.add_node(MAgentNodeEnum.CONTINUE_TO_OVERALL_COMPILE, continue_to_overall_compile)
main_graph.add_node(MAgentNodeEnum.TEST_ALL_CASES, test_all_cases)
main_graph.add_node(MAgentNodeEnum.RECOVER_CODES, recover_codes)
main_graph.add_node(MAgentNodeEnum.POSTPROCESSOR, postprocessor)

main_graph.add_conditional_edges(
    MAgentNodeEnum.MULTY_REPAIRER,
    multi_repairer_choose
)

main_graph.add_conditional_edges(
    MAgentNodeEnum.COMBINE_AND_TEST,
    combine_and_test_choose
)

main_graph.add_conditional_edges(
    MAgentNodeEnum.RECOVER_CODES,
    recover_choose
)

main_graph.add_conditional_edges(
    MAgentNodeEnum.TEST_ALL_CASES,
    test_all_cases_choose
)

main_graph.add_edge(MAgentNodeEnum.PREPROCESSOR, MAgentNodeEnum.MULTY_REPAIRER)
main_graph.add_edge(MAgentNodeEnum.CONTINUE_TO_OVERALL_COMPILE, MAgentNodeEnum.TEST_ALL_CASES)
main_graph.add_edge(MAgentNodeEnum.POSTPROCESSOR, END)

main_graph.set_entry_point(MAgentNodeEnum.PREPROCESSOR)
main_agent = main_graph.compile()

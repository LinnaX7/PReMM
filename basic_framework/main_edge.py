import utils
from basic_framework.all_enum import MAgentNodeEnum
from basic_framework.agent_state import MAgentState, RepairStateEnum


def multi_repairer_choose(m_state: MAgentState):
    for a_state in m_state.get('agent_states'):
        if a_state.get('repair_state').get('repair_result') == RepairStateEnum.COMPILE_ERROR or a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FORMAT_ERROR or a_state.get('repair_state').get('repair_result') == RepairStateEnum.NOT_REPAIRED:
            return MAgentNodeEnum.POSTPROCESSOR
    return MAgentNodeEnum.COMBINE_AND_TEST


def combine_and_test_choose(m_state: MAgentState):
    if m_state.get('repair_result') == RepairStateEnum.REPAIR_TEST_SUCCESS:
        if len(m_state['merged_agents']) > 1:
            return MAgentNodeEnum.CONTINUE_TO_OVERALL_COMPILE
        else:
            return MAgentNodeEnum.TEST_ALL_CASES
    for a_state in m_state.get('agent_states'):
        if a_state.get('repair_state').get('repair_count') >= utils.MAX_ITERATIONS:
            return MAgentNodeEnum.POSTPROCESSOR
    return MAgentNodeEnum.MULTY_REPAIRER


def test_all_cases_choose(m_state: MAgentState):
    if m_state.get('repair_result') == RepairStateEnum.REPAIR_SUCCESS:
        return MAgentNodeEnum.POSTPROCESSOR
    return MAgentNodeEnum.RECOVER_CODES


def recover_choose(m_state: MAgentState):
    for a_state in m_state.get('agent_states'):
        if a_state.get('repair_state').get('repair_count') >= utils.MAX_ITERATIONS:
            return MAgentNodeEnum.POSTPROCESSOR
    return MAgentNodeEnum.MULTY_REPAIRER

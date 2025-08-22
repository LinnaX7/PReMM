import utils
from basic_framework.all_enum import AgentNodeEnum
from basic_framework.agent_state import AgentState, RepairStateEnum
from langgraph.graph import END


def start_node_choose(state: AgentState):
    if utils.Enable_DualAgent:
        return AgentNodeEnum.FAULT_ANALYZER
    else:
        return AgentNodeEnum.REPAIRER


def compile_codes_choose(state: AgentState):
    if state.get('repair_state').get('repair_result') == RepairStateEnum.COMPILE_SUCCESS:
        return AgentNodeEnum.RECOVER_CODES
    else:
        return AgentNodeEnum.RECOVER_CODES


def fault_analysis_choose(state: AgentState):
    if (state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_TEST_SUCCESS or
            state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_SUCCESS):
        return END
    elif state.get('fault_analysis_success'):
        return AgentNodeEnum.REPAIRER
    elif state.get('repair_state').get('repair_count') >= utils.MAX_ITERATIONS:
        return END
    else:
        return AgentNodeEnum.FAULT_ANALYZER


def repair_choose(state: AgentState):
    if (state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_TEST_SUCCESS or
            state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_SUCCESS):
        return END
    if (state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_EXCEPTION or
            state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FORMAT_ERROR) or state.get('repair_state').get('repair_result') == RepairStateEnum.NOT_REPAIRED:
        if state.get('repair_state').get('repair_count') >= utils.MAX_ITERATIONS:
            return END
        if utils.Enable_DualAgent:
            return AgentNodeEnum.FAULT_ANALYZER
        else:
            return AgentNodeEnum.REPAIRER
    else:
        return AgentNodeEnum.MODIFY_AND_COMPILE_CODES


def recover_choose(state: AgentState):
    if (state.get('repair_state').get('repair_result') == RepairStateEnum.COMPILE_SUCCESS or
            state.get('repair_state').get('repair_count') >= utils.MAX_ITERATIONS):
        return END
    else:
        if utils.Enable_DualAgent:
            return AgentNodeEnum.FAULT_ANALYZER
        else:
            return AgentNodeEnum.REPAIRER

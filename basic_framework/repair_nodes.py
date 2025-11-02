import json

from langchain_core.prompts import ChatPromptTemplate

import utils
from Config.prompt import PROMPT_TEMPLATE, FAULT_ANALYSIS_EXPERT, PROGRAM_REPAIR_EXPERT
from basic_framework.prompt import *
from utils import modify_files, recover_files, encoding_count, stream_message


async def fault_analyzer(a_state: AgentState):
    if (a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_TEST_SUCCESS
            or a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_SUCCESS):
        return a_state

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    fault_analysis_expert = FAULT_ANALYSIS_EXPERT
    fault_analysis_expert['description'] = get_fault_programs_pfl_prompt(a_state.get("fault_codes")) + get_role_prompt(
        "fault_analyzer", a_state)
    fault_analysis_expert['expected_output'] = get_output_prompt("fault_analyzer", a_state)
    prompt_input = prompt.invoke(fault_analysis_expert)
    if encoding_count(prompt_input.messages[0].content) >= 32768:
        print("Token too long... Failed to analysis")
        a_state["fault_analysis_success"] = False
        a_state['repair_state']['repair_count'] = utils.MAX_ITERATIONS
        return a_state
    print(prompt_input.messages[0].content)
    utils.Repair_Process_Logger.log(prompt_input.messages[0].content)
    await stream_message(utils.websocket_maps.get(a_state.get('websocket_id')), "user",
                         prompt_input.messages[0].content)
    # try:
    # response = utils.CUSTOM_MODEL.invoke(prompt_input)
    # if response is not None:
    #     result = response.content
    #     a_state['repair_state']['fault_analysis_result'] = result[result.find('['):-1]
    #     a_state['repair_state']['prompt_tokens'] += response.response_metadata.get('token_usage').get('prompt_tokens')
    #     a_state['repair_state']['completion_tokens'] += response.response_metadata.get('token_usage').get('completion_tokens')
    #     utils.Repair_Process_Logger.log(response.content)
    #     print(response.content)
    #     a_state["fault_analysis_success"] = True
    #     return a_state
    full_response = ""
    websocket = utils.websocket_maps.get(a_state.get('websocket_id'))
    full_response = await utils.agent_stream_message(websocket, "fault_analysis", prompt_input)
    print()  # 换行

    if full_response:
        # 处理完整的响应
        a_state['repair_state']['fault_analysis_result'] = full_response[full_response.find('['):-1]
        # utils.Repair_Process_Logger.log(full_response)
        # 注意：流式输出可能无法直接获取token统计信息
        # 可能需要通过其他方式获取或估算token数量
        utils.Repair_Process_Logger.log(full_response)
        a_state["fault_analysis_success"] = True
        # a_state['repair_state']['prompt_tokens'] += full_response.response_metadata.get('token_usage').get('prompt_tokens')
        #     a_state['repair_state']['completion_tokens'] += response.response_metadata.get('token_usage').get('completion_tokens')
    else:
        a_state["fault_analysis_success"] = False

    return a_state

    # except Exception as e:
    #     print("Analysis failed!")
    #     a_state["fault_analysis_success"] = False
    #     a_state['repair_state']['repair_count'] += 1
    #     return a_state


async def repairer(a_state: AgentState):
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    program_repair_expert = PROGRAM_REPAIR_EXPERT
    program_repair_expert['description'] = get_fault_programs_pfl_prompt(a_state.get("fault_codes")) + get_role_prompt(
        "repairer", a_state)
    program_repair_expert['expected_output'] = get_output_prompt('repairer', a_state)
    prompt_input = prompt.invoke(program_repair_expert)
    print(prompt_input.messages[0].content)
    utils.Repair_Process_Logger.log(prompt_input.messages[0].content)
    await stream_message(utils.websocket_maps.get(a_state.get('websocket_id')), "user",
                         prompt_input.messages[0].content)
    if encoding_count(prompt_input.messages[0].content) >= 32768:
        print("Token too long... Failed to repair")
        a_state['repair_state']['repair_count'] = utils.MAX_ITERATIONS
        return a_state
    # response = utils.CUSTOM_MODEL.invoke(prompt_input)
    # result = response.content
    websocket = utils.websocket_maps.get(a_state.get('websocket_id'))
    result = await utils.agent_stream_message(websocket, "repair", prompt_input)
    utils.Repair_Process_Logger.log(result)
    # print(result)
    # a_state['repair_state']['prompt_tokens'] += response.response_metadata.get('token_usage').get('prompt_tokens')
    # a_state['repair_state']['completion_tokens'] += response.response_metadata.get('token_usage').get(
    #     'completion_tokens')
    if result.find("```json")!=-1:
        result = result[result.find("```json"):-1]
    result = result[result.find('['): result.rfind(']') + 1]
    a_state['repair_state']['repair_history'] = result
    try:
        # result = json.loads(result)
        result = eval(result)
        if result is not None:
            format_result, format_info = check_repair_codes(result, a_state)
            if format_result:
                a_state['repair_state']['repair_result'] = RepairStateEnum.REPAIR_FORMAT_SUCCESS
                a_state['repair_state']['repair_history'] = result
            else:
                a_state['repair_state']['repair_history'] = result
                a_state['repair_state']['repair_result'] = RepairStateEnum.REPAIR_FORMAT_ERROR
                a_state['repair_state']['repair_exception'] = format_info
                utils.Repair_Process_Logger.log(f"Format Error! {format_info}\n")
                print(f"Format Error! {format_info}\n")
    except Exception as e:
        print(result)
        a_state['repair_state']['repair_history'] = result
        a_state['repair_state']['repair_result'] = RepairStateEnum.REPAIR_FORMAT_ERROR
        a_state['repair_state']['repair_exception'] = str(e)
        print(str(e))
        utils.Repair_Process_Logger.log("Format Error!\n")
        utils.Repair_Process_Logger.log(str(e))
    a_state['repair_state']['repair_count'] += 1
    return a_state


def process(strsss):
    substr = strsss.split("(")[0]
    substr2 = strsss.split("(")[1]
    substr2 = substr2.replace(" ", "")
    return substr + "(" + substr2


def check_repair_codes(result, a_state: AgentState):
    for repaired_code_info in result:
        method_signature = repaired_code_info.get("fault_method_signature")
        if method_signature is None:
            print("Pay attention to the output of fault_method_signature!")
            return False, "Pay attention to the output of fault_method_signature!"
        if not method_signature.startswith("<"):
            method_signature = "<" + method_signature
        if not method_signature.endswith(">"):
            method_signature = method_signature + ">"
        method_signature = process(method_signature)
        fault_code_info = a_state.get('fault_codes').get(method_signature)

        if fault_code_info is None:
            if len(a_state.get('fault_codes')) > 1:
                print("Pay attention to the output of fault_method_signature!")
                return False, "Pay attention to the output of fault_method_signature!"
            else:
                fault_code_info = list(a_state.get('fault_codes').values())[0]
        repair_code = repaired_code_info.get("repair_code")
        if repair_code is None:
            print("Pay attention to the output of repair_code!")
            return False, "Pay attention to the output of repair_code!"
        if isinstance(repair_code, list):
            repair_code = repair_code[0]
        fault_code_info['repaired_code'] = repair_code
    return True, ""


async def modify_and_compile_codes(a_state: AgentState):
    modify_files(a_state.get('bug_benchmark').get_work_dir(), a_state.get('fault_codes_list'))
    compile_result, compile_error_info = a_state.get('bug_benchmark').compile_files(a_state.get('fault_files'))
    if compile_result:
        a_state['repair_state']['repair_result'] = RepairStateEnum.COMPILE_SUCCESS
        a_state['compile_error_info'] = ""
        await utils.stream_message(utils.websocket_maps.get(a_state.get('websocket_id')),
                                   "validation",
                                   f"The invocation-related patch is compiled successfully!")

    else:
        a_state['repair_state']['repair_result'] = RepairStateEnum.COMPILE_ERROR
        a_state['compile_error_info'] = compile_error_info
        utils.Repair_Process_Logger.log("Compile Error!\n")
        utils.Repair_Process_Logger.log(compile_error_info)
        print("Compile Error!")
        print(compile_error_info)
        await utils.stream_message(utils.websocket_maps.get(a_state.get('websocket_id')),
                                   "validation",
                                   f"The invocation-related patch is compiled unsuccessfully with the following error:{compile_error_info}")
    return a_state


async def recover_codes(a_state: AgentState):
    # recover code
    recover_files(a_state.get('bug_benchmark').get_work_dir(), a_state.get('fault_files'))
    a_state.get('bug_benchmark').recover_files(a_state.get('fault_files'))
    return a_state

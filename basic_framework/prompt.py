import utils
from basic_framework.agent_state import AgentState, RepairStateEnum


def get_fault_programs_pfl_prompt(fault_codes: dict):
    content = "The following codes are buggy:\n"
    i = 1
    for fault_signature, fault_code_info in fault_codes.items():
        content += f"The No.{i} fault method is:\n"
        content += f"\"fault_method_signature\": {fault_signature}\n"
        content += f"\"fault_code\":\n{fault_code_info['fault_code']}\n"
        content += f"where lines in {fault_code_info.get('fault_lines')} are suspicious and these suspicious codes are {fault_code_info.get('fault_line_codes')}.\n"
        i += 1
    return content


def get_test_info_prompt(a_state: AgentState):
    return "".join(
    ["## Failing Test Cases\n",
     "The codes fail on the following test cases:\n",f"{a_state.get('failed_test_cases')[:min(utils.PROVIDED_TEST_CASE_NUM, len(a_state.get('failed_test_cases')))]}.\n"]
    )


def get_invocation_chain_prompt(a_state: AgentState):
    return "".join(
    ["## Dependency Relationships with Test Cases\n"," These are the invocation chains from the failing test cases to the faulty methods. "
                                                     "Consider how changes may affect these relationships to ensure aligned functionality.\n",
    f"{a_state.get('relative_suspicious_paths')}\n"])


def get_similar_codes_prompt(a_state: AgentState):
    content = ""
    similar_code_token = 0
    for fault_signature, fault_code_info in a_state.get('fault_codes').items():
        if len(fault_code_info.get('similar_methods')) != 0:
            content += f"Similar code segments for {fault_signature} are:\n"
            for similar_code in fault_code_info.get('similar_methods'):
                similar_code_token += utils.cal_token(similar_code)
                if similar_code_token > 3000:
                    break
                content += f"{similar_code}\n"
    if similar_code_token > 0:
        return "".join([
            "## Similar Code Search Results\n",
            "Here are similar code snippets from the current repository. Use these patterns to guide potential "
            "changes in the faulty methods.\n",
            f"{content}\n"])
    return ""


def get_key_tokens_prompt(a_state: AgentState):
    return "".join([
        "## Key tokens mined from the Faulty Classes\n",
        "Here are key tokens mined from the faulty classes. Use these as a structural guide and incorporate any "
        "unknown tokens as they may provide useful context for your repair.\n",
        f"{a_state.get('key_tokens')}\n"])


def get_role_prompt(role, a_state: AgentState):
    prompt = ""
    if role == 'fault_analyzer':
        if utils.Test_Case_Prompt:
            prompt += get_test_info_prompt(a_state)
        if utils.Invocation_Chain_Prompt:
            prompt += get_invocation_chain_prompt(a_state)
        if utils.Similar_Codes_Prompt:
            prompt += get_similar_codes_prompt(a_state)
        if a_state.get('repair_state').get('repair_result') == RepairStateEnum.NOT_REPAIRED:
            prompt += "".join([
            "Based on the marked suspicious code lines, the provided test cases and the above additional contextual information, analyze these faulty codes step-by-step, examining each piece of code individually.\n "
            "Focus specifically on the following:\n",
            "1. Carefully examine the input and output of the failing test cases to determine how they relate to the suspicious code lines.\n",
            "2. Identify the exact reasons these lines fail to produce the expected results as defined by the test cases.\n",
            "3. Provide a clear and accurate error analysis that precisely pinpoints the root cause of the issues, ensuring that no extraneous modifications or repairs are suggested.\n"])

            return prompt
        else:
            if a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FORMAT_ERROR:
                error_prompt = f"The Repair Expert tries to repair the codes. However, Its output have format errors, please let the Repairer Expert to pay attention to the output format.\n"
            else:
                error_prompt = "The Repair Expert tries to repair the codes, which might be incorrect as follows:\n"
                for repair in a_state.get('repair_state').get('repair_history'):
                    error_prompt += (f"For fault method {repair.get('fault_method_signature')},\n" + str(repair.get(
                        'repair_code')) + "\n")
                error_prompt += f"However, the fixed version is still not correct, it encounters the following errors:\n"
                if a_state.get('repair_state').get('repair_result') == RepairStateEnum.COMPILE_ERROR:
                    error_prompt += f"Codes have the following compilation error: {a_state.get('compile_error_info')[:min(len(a_state.get('compile_error_info')), 300)]}.\n"
                elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_EXCEPTION:
                    error_prompt += (
                        f"Codes can be compiled, but during the test phase, it encounters the following exception:\n"
                        f"{a_state.get('repair_state').get('repair_exception')[:min(len(a_state.get('repair_state').get('repair_exception')), 300)]}.\n")
                elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_TEST_FAILED:
                    error_prompt += f"It still failed the following failed test cases: {[test_case_name.get('test_method') for test_case_name in a_state.get('failed_test_cases')]}.\n"
                elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FAILED:
                    error_prompt += f"It passed all the failed test cases, but failed new test cases: \n{a_state.get('failed_test_cases')[:min(utils.PROVIDED_TEST_CASE_NUM, len(a_state.get('failed_test_cases')))]}.\n"
            prompt += f"## Previous Repair Results and Fault Information\n"
            prompt += error_prompt
            prompt += (
                f"Combine the results of the previous repairs with the original faulty code, the failed test cases and the above additional contextual information to perform a more precise fault analysis. Think steps by steps:\n"
                f"1. Analyze the new errors introduced by the repair code and think why these fixes did not fully resolve the issues.\n"
                "2. Re-examine the original faulty code based on the failing test cases to identify the root cause.\n"
                "3. Compare the code before and after the repairs to determine which parts of the fixes were effective and which need further improvement.\n"
                "4. Provide the improved fault analysis of the original faulty code.\n")
            return prompt
    if role == 'repairer':
        if not utils.Enable_DualAgent:
            if utils.Test_Case_Prompt:
                prompt += get_test_info_prompt(a_state)
            if utils.Invocation_Chain_Prompt:
                prompt += get_invocation_chain_prompt(a_state)
            if utils.Similar_Codes_Prompt:
                prompt += get_similar_codes_prompt(a_state)
            if utils.Key_Token_Prompt:
                prompt += get_key_tokens_prompt(a_state)
            if a_state.get('repair_state').get('repair_result') == RepairStateEnum.NOT_REPAIRED:
                prompt += f"Based on the above contextual information, repair the faulty codes step by step.\n"
            else:
                prompt += f"## Previous Repair Results and Fault Information\n"
                prompt += str(a_state.get('repair_state').get('repair_history'))
                if a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FORMAT_ERROR:
                    error_prompt = f"Output have the format error: {a_state.get('repair_state').get('repair_exception')}. Please pay attention to the output format.\n"
                else:
                    error_prompt = ""
                    if a_state.get('repair_state').get('repair_result') == RepairStateEnum.COMPILE_ERROR:
                        error_prompt = f"Codes have the following compilation error: {a_state.get('compile_error_info')[:min(len(a_state.get('compile_error_info')), 300)]}.\n"
                    elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_EXCEPTION:
                        error_prompt = (
                            f"Codes can be compiled, but during the test phase, it encounters the following exception:\n"
                            f"{a_state.get('repair_state').get('repair_exception')[:min(len(a_state.get('repair_state').get('repair_exception')), 300)]}.\n")
                    elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_TEST_FAILED:
                        error_prompt = f"It still failed the following failed test cases: {[test_case_name.get('test_method') for test_case_name in a_state.get('failed_test_cases')]}.\n"
                    elif a_state.get('repair_state').get('repair_result') == RepairStateEnum.REPAIR_FAILED:
                        error_prompt = f"It passed all the failed test cases but failed new test cases: \n{a_state.get('failed_test_cases')[:min(utils.PROVIDED_TEST_CASE_NUM, len(a_state.get('failed_test_cases')))]}.\n"
                prompt = f"\n However, the fixed version is still not correct, with the error info:\n {error_prompt}.\n"
                prompt += "Please repair again. Let's think step by step.\n"
            return prompt
        else:
            prompt += f"Based on the fault analysis result:\n {a_state.get('repair_state').get('fault_analysis_result')}, repair the faulty codes step by step.\n"
            prompt += f"Steps: Focus on the **suspicious lines** in each faulty method and perform the necessary and essential repair actions with no modifying other lines.\n"
            if utils.Key_Token_Prompt:
                prompt += f"Additionally, a list of key tokens mined from the faulty classes are provided, which may provide useful context for your repair:\n {a_state.get('key_tokens')}\n"
            return prompt
    return prompt


def get_output_prompt(role, a_state: AgentState):
    if role == 'fault_analyzer':
        if utils.Similar_Codes_Prompt and len(get_similar_codes_prompt(a_state)) > 0:
            return (
                "Finally, output the final summarized fault analysis results in **concise** language for each target faulty method."
                " Present the output in an array format, where each element is a JSON object containing two or three fields: 'fault_method_signature' (the signature of the "
                "current faulty method), 'learned_reference_code' (If applicable, provide a newly learned code snippet from similar methods as a reference for repairs. If no similar code exists, this field can be omitted.),"
                "and 'fault_analysis_result' (a summary of the fault analysis for the current faulty method)\n"
                "## Constraints\n"
                "Keep your answer concise.")
        return (
            "Finally, output the final summarized fault analysis results in **concise** language for each target faulty method."
            " Present the output in an array format, where each element is a JSON object containing two or three fields: 'fault_method_signature' (the signature of the "
            "current faulty method), and 'fault_analysis_result' (a summary of the fault analysis for the current faulty method)\n"
            "## Constraints\n"
            "Keep your answer concise.")
    if role == 'repairer':
        return "".join([
            "Finally, output the repaired code snippets. Present the output in an array format, where each element is a JSON object containing two fields: "
            " 'repair_code' (the repair code for the entire method),",
        " and 'fault_method_signature' (the signature of the faulty method).\n"])
    return ""

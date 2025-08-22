import os
import json
import shutil
import difflib
import pickle
import time

from langchain_openai import ChatOpenAI
import tiktoken
import jpype
import multiprocessing


def read_json(filepath):
    if os.path.exists(filepath):
        assert filepath.endswith('.json')
        with open(filepath, 'r') as f:
            return json.loads(f.read())
    else:
        print("File path " + filepath + " not exists!")
        return


def get_custom_llm():
    filepath = "Config/llm_config.json"
    config = read_json(filepath)
    model_name = config["CurrentLLM"]
    # if model_name == "Deepseek-V3":
    #     return ChatOpenAI(openai_api_key=config["Deepseek-V3"],
    #                       openai_api_base="https://api.deepseek.com/v1",
    #                       model_name="deepseek-chat", temperature=1), model_name
    # if model_name == "Qwen2.5-32B":
    #     return ChatOpenAI(openai_api_key=config["Qwen2.5-32B"],
    #                       openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    #                       model_name="qwen2.5-32b-instruct", temperature=1), model_name
    # if model_name == "Qwen2.5-72B":
    #     return ChatOpenAI(openai_api_key=config["Qwen2.5-72B"],
    #                       openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    #                       model_name="qwen2.5-72b-instruct", temperature=1), model_name
    # if model_name == "Qwen2.5-72B-Local":
    #     return ChatOpenAI(openai_api_key="EMPTY", openai_api_base="http://114.212.170.115:11288/v1",
    #                model_name="Qwen2.5-72B", temperature=1), model_name
    return ChatOpenAI(openai_api_key=config[model_name].get("api_key"), openai_api_base=config[model_name].get("base_url"),
                   model_name=config[model_name].get("model_name"), temperature=1), model_name

CUSTOM_MODEL, MODEL_NAME = get_custom_llm()
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = "output" + os.sep + MODEL_NAME
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
Repair_Result = False
Repair_Iterative_Count = 0
MAX_ITERATIONS = 1
ANALYSIS_DIR = "analysis_output"
Repair_Process_Logger = None
PROVIDED_TEST_CASE_NUM = 3
Test_Case_Prompt = False
Similar_Codes_Prompt = False
Invocation_Chain_Prompt = False
Key_Token_Prompt = False
Enable_FMC = False
Enable_CX = False
Enable_DualAgent = False
Prompt_Tokens = 0
Completion_Tokens = 0
Total_Prompt_Token = 0
Total_Completion_Token = 0

test_cases_codes_map = {}
repair_agent = None


def get_version_name():
    if (not Enable_FMC) and (not Enable_CX) and (not Enable_DualAgent) and (MAX_ITERATIONS == 1):
        return "PReMM-FCDI"
    if MAX_ITERATIONS > 1:
        if (not Enable_FMC) and (not Enable_CX) and (not Enable_DualAgent):
            return "PReMM-FCD"
        elif (not Enable_CX) and (not Enable_DualAgent):
            return "PReMM-CD"
        elif (not Enable_FMC) and (not Enable_CX):
            return "PReMM-FC"
        elif (not Enable_FMC) and (not Enable_DualAgent):
            return "PReMM-FD"
        elif not Enable_FMC:
            return "PReMM-F"
        elif not Enable_CX:
            return "PReMM-C"
        elif not Enable_DualAgent:
            return "PReMM-D"
        else:
            return "PReMM"


def get_codes_from_file(file_path, begin_line, end_line):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        data = f.readlines()
    code_snippet = ""
    for i in range(begin_line - 1, end_line):
        code_snippet += data[i]
    return code_snippet


def modify_files(base_dir, repair_results: list):
    for repair_result in repair_results:
        file_path = repair_result["file_path"]
        repaired_snippets = repair_result["fault_code_snippets"]
        modify_file(base_dir, file_path, repaired_snippets)


def decode_code_list(code_list):
    for i in range(len(code_list)):
        code_list[i] = code_list[i].replace("irnlgkjidl", "'")


def recover_files(base_dir, file_list):
    for file in file_list:
        recover_file(base_dir, file)


def check_file_list(working_dir, file_list):
    for file in file_list:
        if not os.path.exists(os.path.join(working_dir, file)):
            return False
    return True


def normalize_lines(lines):
    return [line.strip() for line in lines]


def diff_patch(original_file, repair_file, output_file):
    try:
        with open(original_file) as file1:
            file1_text = file1.readlines()
    except Exception as e:
        with open(original_file, encoding='iso-8859-1') as file1:
            file1_text = file1.readlines()
    try:
        with open(repair_file) as file2:
            file2_text = file2.readlines()
    except Exception as e:
        with open(repair_file, encoding='iso-8859-1') as file2:
            file2_text = file2.readlines()
    patch = ""
    file1_text = normalize_lines(file1_text)
    file2_text = normalize_lines(file2_text)
    for line in difflib.unified_diff(
            file1_text, file2_text, fromfile=original_file,
            tofile=repair_file, lineterm=''):
        patch += (line + "\n")
    with open(output_file, "a") as patch_file:
        patch_file.write(patch)
        # os.popen("diff {} {} > {}".format(original_file, repair_file, os.path.join(output_dir, "patch.diff")))
    print("Generate patch diff successfully!")


def recover_file(base_dir, file):
    tmp_d = os.path.join(get_temp_dir(base_dir), os.sep.join(file.split(os.sep)[:-1]))
    source_dir = os.path.join(base_dir, os.sep.join(file.split(os.sep)[:-1]))
    temp_file = os.path.join(tmp_d, file.split(os.sep)[-1])
    os.remove(os.path.join(base_dir, file))
    shutil.copy2(temp_file, source_dir)
    print(f"Recover {file} successfully!")


def encoding_count(input: str) -> int:
    """ token count """
    encoding_name = 'cl100k_base'
    encoding = tiktoken.get_encoding(encoding_name)
    token_integers = encoding.encode(input)
    num_tokens = len(token_integers)
    return num_tokens


def generate_patch_diff(bug_id, working_dir, file_list):
    output_dir = os.path.join(OUTPUT_DIR, bug_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    diff_file = os.path.join(output_dir, f"patch-{MAX_ITERATIONS}.diff")
    for file in file_list:
        repair_file = os.path.join(working_dir, file)
        original_file = os.path.join(get_temp_dir(working_dir), file)
        diff_patch(original_file, repair_file, diff_file)


def generate_patch_file(bug_id, fault_codes_list):
    output_dir = os.path.join(OUTPUT_DIR, bug_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    open(os.path.join(output_dir, f"{bug_id}-{MAX_ITERATIONS}.java"), 'w').close()
    for fault_code in fault_codes_list:
        fault_code_snippets = fault_code["fault_code_snippets"]
        for fault_code_snippet in fault_code_snippets:
            with open(os.path.join(output_dir, f"{bug_id}-{MAX_ITERATIONS}.java"), 'a') as file:
                file.write(fault_code_snippet.get('repaired_code'))


def get_temp_dir(working_dir):
    return "tmp" + os.sep + working_dir


def remove_temp_dir(working_dir):
    temp_dir = get_temp_dir(working_dir)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(working_dir):
        shutil.rmtree(working_dir)


def modify_file(working_dir: str, file: str, repaired_snippets: list):
    folder_list = file.split(os.sep)[:-1]
    temp_dir = os.path.join(get_temp_dir(working_dir), os.sep.join(folder_list))
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    if os.path.exists(os.path.join(temp_dir, os.sep.join(folder_list))):
        os.remove(os.path.join(temp_dir, os.sep.join(folder_list)))
    shutil.copy2(os.path.join(working_dir, file), temp_dir)
    repaired_snippets.sort(key=lambda x: x["line_begin"])
    with open(os.path.join(os.path.join(working_dir, file)), 'r', encoding='utf-8', errors='ignore') as f:
        data = f.readlines()
    begin_index = 0
    new_content = ""
    for repaired_snippet in repaired_snippets:
        for i in range(begin_index, repaired_snippet["line_begin"] - 1):
            new_content += data[i]
        new_content += repaired_snippet["repaired_code"]
        begin_index = repaired_snippet["line_end"]
    for i in range(begin_index, len(data)):
        new_content += data[i]
    with open(os.path.join(working_dir, file), "w") as repaired_file:
        repaired_file.write(new_content)


def modify_file_pre(working_dir: str, code_info):
    with open(os.path.join(os.path.join(working_dir, code_info["file_path"])), 'r', encoding='utf-8', errors='ignore') as f:
        data = f.readlines()
    begin_index = 0
    new_content = ""

    for i in range(begin_index, code_info["start"] - 1):
        new_content += data[i]
    code_info["buggy"] = code_info["buggy"].replace("/* bug is here */", "")
    new_content += code_info["buggy"]
    begin_index = code_info["end"]
    for i in range(begin_index, len(data)):
        new_content += data[i]

    with open(os.path.join(working_dir,  code_info["file_path"]), "w") as repaired_file:
        repaired_file.write(new_content)

def merge_related_functions(methods_tests_map: dict):
    merged_methods = []
    merged_methods_tests_map = {}
    for methods, tests in methods_tests_map.items():
        methods_string = ""
        if isinstance(methods, str):
            methods_string = methods
        elif isinstance(methods, tuple):
            methods_string = ', '.join(map(str, methods))
        if len(merged_methods) == 0:
            merged_methods.append(methods)
        else:
            merged_methods_len = len(merged_methods)
            i = 0
            flag = False
            while i < merged_methods_len:
                t_methods = merged_methods[i]
                t_methods_string = ""
                if isinstance(t_methods, str):
                    t_methods_string = t_methods
                elif isinstance(t_methods, tuple):
                    t_methods_string = ', '.join(map(str, t_methods))
                if t_methods_string.find(methods_string) == -1:
                    if methods_string.find(t_methods_string) != -1:
                        merged_methods[i] = methods
                        tests.extend(methods_tests_map.get(t_methods))
                        flag = True
                        break
                else:
                    flag = True
                    methods_tests_map.get(t_methods).extend(tests)
                    break
                i += 1
            if not flag:
                merged_methods.append(methods)
    for merged_method in merged_methods:
        merged_methods_tests_map[merged_method] = methods_tests_map.get(merged_method)
    return merged_methods_tests_map


def codes_format_transform(code_list: list):
    file_fault_codes_map = {}
    fault_codes = []
    for fault_code_info in code_list:
        file_path = fault_code_info.get('file_path')
        if file_fault_codes_map.get(file_path) is None:
            file_fault_codes_map[file_path] = []
        file_fault_codes_map.get(file_path).append(fault_code_info)
    for file_path, fault_code_snippets in file_fault_codes_map.items():
        fault_codes.append({"file_path": file_path, "fault_code_snippets": fault_code_snippets})
    return fault_codes, list(file_fault_codes_map.keys())


def get_all_similar_methods(fault_codes: dict):
    similar_codes_list = []
    for fault_signature, fault_code_info in fault_codes.items():
        similar_codes = fault_code_info.get("similar_methods")
        similar_codes_list.extend(similar_codes)
    return similar_codes_list




def output_test_cases_codes_map(dataset, bug_id):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(os.path.join(dir_path, 'test_cases_codes_map.pickle'), 'wb') as file:
        pickle.dump(test_cases_codes_map, file)


def load_test_cases_codes_map(dataset, bug_id):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    if os.path.exists(os.path.join(dir_path, 'test_cases_codes_map.pickle')):
        with open(os.path.join(dir_path, 'test_cases_codes_map.pickle'), 'rb') as file:
            return pickle.load(file)
    else:
        return {}


def output_prepare_info(dataset, bug_id, signature_method_map, methods_tests_map,
                        method_test_path_map):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    # with open(os.path.join(dir_path, 'initial_failing_tests.pickle'), 'wb') as file:
    #     pickle.dump(failed_tests, file)
    with open(os.path.join(dir_path, 'signature_method_map.pickle'), 'wb') as file:
        pickle.dump(signature_method_map, file)
    with open(os.path.join(dir_path, 'methods_tests_map.pickle'), 'wb') as file:
        pickle.dump(methods_tests_map, file)
    with open(os.path.join(dir_path, 'method_test_path_map.pickle'), 'wb') as file:
        pickle.dump(method_test_path_map, file)


def load_signature_method_map(dataset, bug_id):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    if os.path.exists(os.path.join(dir_path, 'signature_method_map.pickle')):
        with open(os.path.join(dir_path, 'signature_method_map.pickle'), 'rb') as file:
            return pickle.load(file)
    else:
        return {}


def get_time():
    return time.time()


def load_method_test_path_map(dataset, bug_id):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    if os.path.exists(os.path.join(dir_path, 'method_test_path_map.pickle')):
        with open(os.path.join(dir_path, 'method_test_path_map.pickle'), 'rb') as file:
            return pickle.load(file)
    else:
        return {}


def load_prepare_info(dataset, bug_id):
    dir_path = os.path.join(ANALYSIS_DIR, dataset, bug_id)
    # with open(os.path.join(dir_path, 'initial_failing_tests.pickle'), 'rb') as file:
    #     failed_tests = pickle.load(file)
    with open(os.path.join(dir_path, 'signature_method_map.pickle'), 'rb') as file:
        signature_method_map = pickle.load(file)
    with open(os.path.join(dir_path, 'methods_tests_map.pickle'), 'rb') as file:
        methods_tests_map = pickle.load(file)
    with open(os.path.join(dir_path, 'method_test_path_map.pickle'), 'rb') as file:
        method_test_path_map = pickle.load(file)
    return  signature_method_map, methods_tests_map, method_test_path_map


def cal_token(*args):
    lenth = 0
    for v in args:
        if isinstance(v, int):
            lenth += v * 2
        elif isinstance(v, str):
            lenth += len(v)
        elif isinstance(v, list) and isinstance(v[0], dict):
            lenth += sum([len(vd["content"]) for vd in v])
        elif isinstance(v, list) and isinstance(v[0], dict):
            lenth += sum([cal_token(vd) for vd in v])
    return lenth // 2


def get_test_code(working_dir, test_source_dir, test_class, test_method):
    if test_cases_codes_map.get(f"{test_class}::{test_method}") is None:
        # test_source_dir = "test"
        test_file = os.path.join(working_dir, test_source_dir, "/".join(test_class.split(".")) + ".java")
        codes = get_method_code(test_file, test_method)
        test_cases_codes_map[f"{test_class}::{test_method}"] = codes
    return test_cases_codes_map.get(f"{test_class}::{test_method}")


def get_method_code(file_path, method_name, including_line=-1):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        java_code = f.read()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        data = f.readlines()
    start_line, end_line = get_method_position(java_code, method_name, including_line)
    code_snippet = ""
    for i in range(start_line - 1, end_line):
        code_snippet += data[i]
    return code_snippet


def get_method_position_working(queue, java_code, method_name, in_line):
    jvm_path = jpype.getDefaultJVMPath()
    javaparser_path = os.path.join(".", "java_lib", "context-extractor.jar")
    jpype.startJVM(jvm_path, "-ea", "-Djava.class.path=%s" % javaparser_path)
    JClass = jpype.JClass("ProgramAnalysis")
    position = JClass.getMethodPosition(java_code, method_name, in_line)
    queue.put(str(position))
    # Shut down JVM
    jpype.shutdownJVM()
    return position


def get_method_position(java_code, method_name, in_line=-1):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=get_method_position_working,
                                      args=(queue, java_code, method_name, in_line))
    process.start()
    process.join()
    position = queue.get()
    return int(position.split(",")[0]), int(position.split(",")[1])

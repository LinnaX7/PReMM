import json
import os
import re
import shutil
import signal
import subprocess
import time
import utils
from benchmark.benchmark import Benchmark, BenchmarkRegistry
from logger import Logger

environment_config = utils.read_json("Config/defects4j_environment.json")
JAVA_7_HOME = environment_config["JAVA_7_HOME"]
JAVA_8_HOME = environment_config["JAVA_8_HOME"]
Defects4J_DIR = environment_config["Defects4J_DIR"]
Defects4J_V2_DIR = environment_config["Defects4J_V2_DIR"]
Defects4J_Trans_DIR = environment_config["Defects4J_Trans_DIR"]

JAVA7_CMD = (" && ".join([f"export JAVA_HOME=\"{JAVA_7_HOME}\"", "export CLASS_PATH=\"$JAVA_HOME/lib\"",
                          "export PATH=.$PATH:\"$JAVA_HOME/bin\""]))
JAVA8_CMD = (" && ".join([f"export JAVA_HOME=\"{JAVA_8_HOME}\"", "export CLASS_PATH=\"$JAVA_HOME/lib\"",
                          "export PATH=.:\"$JAVA_HOME/bin\":$PATH"]))
Defects4J_CMD = (" && ".join([JAVA7_CMD, f"export PATH=.:\"{Defects4J_DIR}/framework/bin\":$PATH"]))
Defects4J_V2_CMD = (" && ".join([JAVA8_CMD, f"export PATH=.:\"{Defects4J_V2_DIR}/framework/bin\":$PATH"]))
Defects4J_Trans_CMD = (" && ".join([JAVA8_CMD, f"export PATH=.:\"{Defects4J_Trans_DIR}/framework/bin\":$PATH"]))
TEMP_DIR = environment_config["TEMP_DIR"]


@BenchmarkRegistry.register("defects4j")
class Defects4j(Benchmark):
    def __init__(self, database_name):
        super().__init__(database_name)
        self.compile_jar_path = ""

    def checkout(self, bug_id):
        self.bug_id = bug_id
        self.work_dir = os.path.join(TEMP_DIR, bug_id)
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if not os.path.exists(self.work_dir):
            prepare_project(self.database_name, bug_id, self.work_dir)
        self.compile_jar_path, self.source_dir, self.build_dir, self.test_source_dir, self.test_build_dir = (
            get_necessary_path(self.database_name, self.work_dir))
        self.fault_location_file = fault_locate(self.database_name, bug_id)
        if self.database_name == "defects4j-trans":
            soup_fl_file = os.path.join("datasets", self.database_name, "fault_location", "SoapFL", f"{self.bug_id}",
                                        "result.json")
            with open(soup_fl_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            buggy_methods = data["buggy_methods"]
            self.suspicious_methods = buggy_methods
        try:
            _, self.init_failing_tests = test_project(self.database_name, bug_id, self.work_dir, self.test_source_dir)
        except Exception as e:
            raise Exception("The project failed to init failing test cases (it encounters time out when testing)."
                            " Please check your project.")

    def get_suspicious_method(self, index):
        first_method = self.suspicious_methods[index]
        method_name = first_method.get("method_name", "unknown")
        return [method_name]

    def compile_files(self, files: list):
        try:
            compile_results = compile_files(self.database_name, self.work_dir, self.compile_jar_path, files)
            result = True
            compile_error_info = ""
            if compile_results is not None:
                for compile_result in compile_results:
                    if not compile_result.get('compiled_result'):
                        result = False
                        compile_error_info += compile_result.get('compiled_info')
            return result, compile_error_info
        except Exception as e:
            print(e)
            result = False
            compile_error_info = str(e)
            return result, compile_error_info

    def compile_project(self):
        try:
            compile_project(self.database_name, self.bug_id, self.work_dir)
            return True, ""
        except Exception as e:
            return False, str(e)

    def test_failed_test_cases(self, failed_test_cases: list):
        test_result = run_test_cases(self.database_name, self.work_dir, self.test_source_dir, failed_test_cases)
        return test_result

    def test_project(self):
        failing_test_num, test_result = test_project(self.database_name, self.bug_id, self.work_dir,
                                                     self.test_source_dir)
        return failing_test_num, test_result

    def recover_files(self, file_list):
        self.compile_files(file_list)

    def get_all_bugs(self):
        d4j_v1_2 = {
            "Chart": {
                "all": list(range(1, 27)),  # 26 bugs (1-26)
                "excluded": []  # No excluded bugs in Chart
            },
            "Closure": {
                "all": list(range(1, 134)),  # 133 bugs (1-133)
                "excluded": [26, 43, 108]  # No excluded bugs in Closure v1.2
            },
            "Lang": {
                "all": list(range(1, 66)),  # 65 bugs (1-65)
                "excluded": [23, 25, 32, 56]  # Other Bugs beyond sing-method or multi-method bugs
            },
            "Math": {
                "all": list(range(1, 107)),  # 106 bugs (1-106)
                "excluded": [6, 12, 104]  # Other Bugs beyond sing-method or multi-method bugs
            },
            "Mockito": {
                "all": list(range(1, 39)),  # 38 bugs (1-38)
                "excluded": [14, 17, 19, 23, 26]  # No excluded bugs in Mockito
            },
            "Time": {
                "all": list(range(1, 28)),  # 27 bugs (1-27)
                "excluded": [11]  # Other Bugs beyond sing-method or multi-method bugs
            }
        }

        d4j_v2 = {
            "Cli": {
                "all": list(range(1, 6)) + list(range(7, 41)),  # 1-5,7-40 (39 bugs)
                "excluded": [7, 36]  # Other Bugs beyond sing-method or multi-method bugs
            },
            "Closure": {
                "all": list(range(134, 177)),  # 134-176 (43 bugs)
                "excluded": [134, 137, 144, 148, 149, 151, 153, 154, 155, 156, 157, 158, 162, 163, 165, 167, 169, 175]
            },
            "Codec": {
                "all": list(range(1, 19)),  # 1-18 (18 bugs)
                "excluded": [11, 12, 14, 16]  # checked
            },
            "Collections": {
                "all": list(range(25, 29)),  # 25-28 (4 bugs)
                "excluded": [27, 28]  # checked
            },
            "Compress": {
                "all": list(range(1, 48)),  # 1-47 (47 bugs)
                "excluded": [2, 3, 9, 22, 29, 33]  # checked
            },
            "Csv": {
                "all": list(range(1, 17)),  # 1-16 (16 bugs)
                "excluded": [12, 13, 16]  # checked
            },
            "Gson": {
                "all": list(range(1, 19)),  # 1-18 (18 bugs)
                "excluded": [3, 8, 9]  # checked
            },
            "JacksonCore": {
                "all": list(range(1, 27)),  # 1-26 (26 bugs)
                "excluded": [13, 16]  # checked
            },
            "JacksonDatabind": {
                "all": list(range(1, 113)),  # 1-112 (112 bugs)
                "excluded": [10, 14, 15, 18, 20, 21, 22, 23, 26, 30, 31, 38, 40, 50, 53, 55, 59, 60, 66, 72, 78, 84, 86,
                             87, 89, 92, 103, 105, 109]
            },
            "JacksonXml": {
                "all": list(range(1, 7)),  # 1-6 (6 bugs)
                "excluded": [2, 6]  # checked
            },
            "Jsoup": {
                "all": list(range(1, 94)),  # 1-93 (93 bugs)
                "excluded": [3, 4, 7, 9, 14, 17, 21, 25, 30, 31, 36, 56, 66, 69, 71, 87, 92]
            },
            "JxPath": {
                "all": list(range(1, 23)),  # 1-22 (22 bugs)
                "excluded": [7, 9, 13, 18]  # checked
            }
        }
        if self.database_name == "defects4jv1.2":
            d4j_bus = []
            for project_name, project_info in d4j_v1_2.items():
                for bug_id in project_info["all"]:
                    if bug_id not in project_info["excluded"]:
                        d4j_bus.append(project_name + "-" + str(bug_id))
            return d4j_bus
        elif self.database_name == "defects4jv2":
            d4jv2_bugs = []
            for project_name, project_info in d4j_v2.items():
                for bug_id in project_info["all"]:
                    if bug_id not in project_info["excluded"]:
                        d4jv2_bugs.append(project_name + "-" + str(bug_id))
            return d4jv2_bugs
        elif self.database_name == "defects4j-trans":
            json_file = os.path.join(utils.ROOT_PATH, "datasets", "defects4j-trans",
                                     "enhanced_single_function_repair_trans_final_fl.json")
            data = utils.read_json(json_file)
            return list(data.keys())


def get_loc_file(dataset_name: str, bug_id, perfect):
    dirname = utils.ROOT_PATH
    if perfect:
        loc_file = os.path.join("datasets", dataset_name.lower(), "fault_location", "groundtruth",
                                bug_id.split("-")[0].lower(),
                                bug_id.split("-")[1])
    else:
        loc_file = os.path.join("datasets", dataset_name.lower(), "fault_location", "ochiai",
                                bug_id.split("-")[0].lower(),
                                bug_id.split("-")[1])
    loc_file = os.path.join(dirname, loc_file)
    if os.path.isfile(loc_file):
        return os.path.abspath(loc_file)
    else:
        # print(loc_file)
        return ""


def fault_locate(dataset_name, bug_id, perfect=True):
    loc_file = get_loc_file(dataset_name, bug_id, perfect)
    return loc_file


def run_command(command, logger, cwd=None):
    try:
        start_time = time.time()
        """Run a command in the shell and print its output."""
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300)
        logger.log(result.stdout)
        if result.returncode != 0:
            logger.log(result.stderr)
            raise Exception(f"{result.stderr}")
        logger.log(f"cmd execution time: {time.time() - start_time}")
    except subprocess.TimeoutExpired as e:
        logger.log(f"Time out: {str(e)}")
        raise Exception(f"Time out: {str(e)}")


def prepare_project(database_name, bug_id, working_dir):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    project_name = bug_id.split("-")[0]
    idd = int(bug_id.split("-")[1])
    checkout_cmd = f"defects4j checkout -p {project_name} -v {idd}b -w {working_dir}"
    cd_working_dir_cmd = f"cd {working_dir}"
    compile_cmd = "defects4j compile"
    # test_cmd = "defects4j test"
    # test_methods = f"defects4j export -w {working_dir} -p tests.trigger"
    execute_cmd = " && ".join([prepare_dataset_env_cmd, checkout_cmd, cd_working_dir_cmd, compile_cmd])
    # execute_cmd = " && ".join([prepare_dataset_env_cmd, test_methods])
    if not os.path.exists("output"):
        os.makedirs("output")
    logger = Logger(os.path.join("output", bug_id + "_result.txt"))

    run_command(execute_cmd, logger)
    # if database_name == "defects4j-trans":
    #     init_defects4j_trans_env(bug_id, working_dir)
    #     compile_project(database_name, bug_id, working_dir)


def init_defects4j_trans_env(bug_id, working_dir):
    json_file = f"datasets/defects4j-trans/enhanced_single_function_repair_trans_final_fl.json"
    single_function_bugs = utils.read_json(json_file)
    code_info = single_function_bugs.get(bug_id)
    print(
        f"Initializing defects4j-trans ({bug_id}):\n1. Replace the original code with transform code.\n2. Compile Project.")
    utils.modify_file_pre(working_dir, code_info)


def get_test_code(working_dir, test_source_dir, test_name):
    test_class = test_name.split("::")[0]
    test_method = test_name.split("::")[1]
    return utils.get_test_code(working_dir, test_source_dir, test_class, test_method)


def run_single_test(database_name, working_dir, test_source_dir, test_case):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    test_cmd = f"defects4j test -w {working_dir} -t {test_case}"
    execute_cmd = " && ".join([prepare_dataset_env_cmd, test_cmd])
    error_file = open("stderr.txt", "wb")
    test_result = subprocess.Popen(execute_cmd, shell=True, stdout=subprocess.PIPE, stderr=error_file, bufsize=-1,
                                   start_new_session=True)
    while_begin = time.time()
    error_string = ""
    Returncode = ""
    timed_out = False
    failing_tests = []
    while True:
        Flag = test_result.poll()
        if Flag == 0:
            Returncode = test_result.stdout.readlines()  # child.stdout.read()
            # print(b"".join(Returncode).decode('utf-8'))
            # error_file.close()
            break
        elif Flag != 0 and Flag is not None:
            compile_fail = True
            error_file.close()
            with open("stderr.txt", "rb") as f:
                r = f.readlines()
            for line in r:
                if re.search(':\serror:\s', line.decode('utf-8')):
                    error_string = line.decode('utf-8')
                    break
            failing_test = {"test_method": test_case}
            failing_test["test_case_code"] = get_test_code(working_dir, test_source_dir,
                                                           failing_test.get("test_method"))
            failing_test["failing_info"] = error_string
            return {test_case: failing_test}
        elif time.time() - while_begin > 15:
            error_file.close()
            # print('time out error')
            os.killpg(os.getpgid(test_result.pid), signal.SIGTERM)
            timed_out = True
            failing_test = {"test_method": test_case}
            failing_test["test_case_code"] = get_test_code(working_dir, test_source_dir,
                                                           failing_test.get("test_method"))
            failing_test["failing_info"] = "Time out error"
            return {test_case: failing_test}
        else:
            time.sleep(1)
    log = Returncode
    if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
        return {}
    else:
        return get_test_info(database_name, working_dir, test_source_dir)


def run_test_cases(database_name, working_dir, test_source_dir, test_cases):
    test_results = {}
    for test_case in test_cases:
        try:
            test_result = run_single_test(database_name, working_dir, test_source_dir, test_case)
            test_results.update(test_result)
        except Exception as e:
            test_result = {}
            failing_test = {"test_method": test_case}
            failing_test["test_case_code"] = get_test_code(working_dir, test_source_dir,
                                                           failing_test.get("test_method"))
            failing_test["failing_info"] = f"Exception: {e}"
            test_result[test_case] = failing_test
            test_results.update(test_result)

    return test_results


def test_project(database_name, bug_id, working_dir, test_source_dir):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    cd_working_dir_cmd = f"cd {working_dir}"
    test_cmd = f"defects4j test"
    execute_cmd = " && ".join([prepare_dataset_env_cmd, cd_working_dir_cmd, test_cmd])
    if not os.path.exists("output"):
        os.makedirs("output")
    logger = Logger(os.path.join("output", bug_id + "_result.txt"))
    try:
        run_command(execute_cmd, logger)
        with open(os.path.join("output", bug_id + "_result.txt"), 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()
            failing_tests = int(first_line.split(": ")[1])
        if failing_tests < 30:
            return failing_tests, get_test_info(database_name, working_dir, test_source_dir, failing_tests)
        else:
            # return failing_tests, get_test_info(database_name, working_dir, test_source_dir, 30)
            return failing_tests, {}
    except Exception as e:
        raise Exception(e)
    # return 1, e


def compile_project(database_name, bug_id, working_dir):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    cd_working_dir_cmd = f"cd {working_dir}"
    test_cmd = f"defects4j compile"
    execute_cmd = " && ".join([prepare_dataset_env_cmd, cd_working_dir_cmd, test_cmd])
    if not os.path.exists("output"):
        os.makedirs("output")
    logger = Logger(os.path.join("output", bug_id + "_result.txt"))
    run_command(execute_cmd, logger)


def get_test_info(database_name, working_dir, test_source_dir, num_tests=1):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    cd_working_dir_cmd = f"cd {working_dir}"
    cat_test_info = "cat failing_tests"
    execute_cmd = " && ".join([prepare_dataset_env_cmd, cd_working_dir_cmd, cat_test_info])
    test_result = subprocess.Popen(execute_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                   start_new_session=True)
    failing_tests = {}
    test_info = test_result.stdout.read().decode("utf-8")
    flag = False
    failing_test = {}
    i = 0
    for line in test_info.split("\n"):
        if line.startswith("---"):
            flag = True
            failing_test["test_method"] = line.split(" ")[1]
            failing_test["test_case_code"] = get_test_code(working_dir, test_source_dir,
                                                           failing_test.get("test_method"))
        elif flag:
            flag = False
            failing_test["failing_info"] = line
            failing_tests[failing_test.get("test_method")] = failing_test
            failing_test = {}
            i += 1
            if i >= num_tests:
                break
    return failing_tests


def get_necessary_path(database_name, working_dir):
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    source_dir = os.popen(
        " && ".join([prepare_dataset_env_cmd, "defects4j export -p dir.src.classes -w " + working_dir])).readlines()[
        -1].strip()
    class_path_cmd = " && ".join([prepare_dataset_env_cmd, "defects4j export -p cp.compile -w " +
                                  working_dir])
    compile_jar_path = os.popen(class_path_cmd).readlines()[-1].strip()
    classes_build_dir = \
        os.popen(
            prepare_dataset_env_cmd + " && " + "defects4j export -p dir.bin.classes -w " + working_dir).readlines()[
            -1].strip()
    test_build_dir = os.popen(
        prepare_dataset_env_cmd + " && " + "defects4j export -p cp.test -w " + working_dir).readlines()[
        -1].strip()
    for path in test_build_dir.split(os.pathsep):
        if path.endswith("test") or path.endswith("tests") or path.endswith("test-classes"):
            if path.find("src") != -1:
                continue
            if path.find(working_dir) != -1:
                test_build_dir = path[path.find(working_dir) + len(working_dir) + 1:]
            else:
                test_build_dir = path
            break
    test_source_dir = os.popen(" && ".join([prepare_dataset_env_cmd, "defects4j export -p dir.src.tests -w " +
                                            working_dir])).readlines()[-1].strip()
    return compile_jar_path, source_dir, classes_build_dir, test_source_dir, test_build_dir


def javac_compile(database_name, working_dir, classes_path, target_file_path):
    compiled_result = {}
    prepare_dataset_env_cmd = ""
    if database_name == "defects4jv1.2":
        prepare_dataset_env_cmd = Defects4J_CMD
    elif database_name == "defects4jv2":
        prepare_dataset_env_cmd = Defects4J_V2_CMD
    elif database_name == "defects4j-trans":
        prepare_dataset_env_cmd = Defects4J_Trans_CMD
    cd_working_dir_cmd = f"cd {working_dir}"
    javac_compile_cmd = f"javac -cp {classes_path} {os.path.join(working_dir, target_file_path)}"
    exec_cmd = " && ".join([prepare_dataset_env_cmd, cd_working_dir_cmd, javac_compile_cmd])
    result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
    compiled_info = result.stdout
    if result.returncode != 0:
        compiled_result["compiled_file"] = target_file_path
        compiled_result["compiled_result"] = False
        compiled_result["compiled_info"] = result.stderr
    else:
        compiled_result["compiled_file"] = target_file_path
        compiled_result["compiled_result"] = True
        compiled_result["compiled_info"] = compiled_info
    return compiled_result


def compile_files(database_name, working_dir, class_path, file_list: list):
    compile_results = []
    for file_path in file_list:
        compile_result = javac_compile(database_name, working_dir, class_path, file_path)
        compile_results.append(compile_result)
    return compile_results

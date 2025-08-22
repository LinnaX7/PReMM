import os
import re
import subprocess

import utils
from benchmark.benchmark import Benchmark, BenchmarkRegistry
import shutil


@BenchmarkRegistry.register("gitbug-java")
class GitBugJava(Benchmark):
    def __init__(self, database_name):
        super().__init__(database_name)
        self.database_name = database_name

    def checkout(self, bug_id):
        self.bug_id = bug_id
        self.work_dir = os.path.join("/tmp", "gitbug-java", bug_id)

        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        if not os.path.exists(self.work_dir):
            check_out(bug_id, self.work_dir)
            run_work_flow(self.work_dir)

        self.source_dir, self.build_dir, self.test_source_dir, self.test_build_dir \
            = init_gitbug_project_structure(bug_id)
        self.fault_location_file = os.path.join(utils.ROOT_PATH, "datasets", self.database_name, "fault_location",
                                                bug_id)
        self.init_failing_tests = get_init_test_info(self.work_dir, self.test_source_dir)

    def compile_files(self, files: list):
        try:
            run_work_flow(self.work_dir)
            return get_compile_errors(self.work_dir)
        except subprocess.TimeoutExpired:
            return False, "Build Time Out!"

    def compile_project(self):
        try:
            run_work_flow(self.work_dir)
            return get_compile_errors(self.work_dir)
        except subprocess.TimeoutExpired:
            return False, "Build Time Out!"

    def test_failed_test_cases(self, failed_test_cases: list):
        test_info = {}
        # key is test_method in the format of "ClassName::methodName"
        # value is a dict containing the two fields: "failing_info" and "test_code"
        # _, test_info = get_test_info(self.work_dir, self.test_source_dir)
        json_file = os.path.join(self.work_dir, ".gitbug-java", "test-results.json")
        data = utils.read_json(json_file)
        failed_tests = data.get("failed_tests")

        if len(failed_tests) == 0:
            return {}
        for failed_test in failed_tests:
            name = failed_test.get('name')
            name = refine_test_name(name)
            test_name = f"{failed_test.get('classname')}::{name}"
            if self.init_failing_tests.get(test_name) is not None:
                test_info[test_name] = self.init_failing_tests[test_name]
        return test_info

    def recover_files(self, file_list):
        self.compile_files(file_list)

    def test_project(self):
        # test_info = {}
        # key is test_method in the format of "ClassName::methodName"
        # value is a dict containing the two fields: "failing_info" and "test_case_code"
        # return the number of failing tests, and the failing test info
        num, test_info = get_test_info(self.work_dir, self.test_source_dir)
        return num, test_info

    def get_all_bugs(self):
        path = os.path.join(utils.ROOT_PATH, "datasets", "gitbug-java", "bug_pfl.json")
        bug_list = list(utils.read_json(path).keys())
        return bug_list


def refine_test_name(name):
    if name.find("[") != -1 and name.find("(") != -1:
        name = name[:name.rfind("(")]
    if name.find("[") != -1 and name.find("{") != -1:
        name = name[:name.rfind("{")]
    if name.endswith("()"):
        name = name[:-2]
    return name


def check_out(bug_id, work_dir):
    gitbug_java_env = utils.read_json(os.path.join(utils.ROOT_PATH, "Config", "gitbug_java_environment.json"))
    command = (f"cd {gitbug_java_env['gitbug_repo']} && export PATH=\"$(pwd):$(pwd)/bin:$PATH\" "
               f"&& conda run -n {gitbug_java_env['conda_env_name']} gitbug-java checkout {bug_id} {work_dir}")
    print(command)
    result = subprocess.run(command, shell=True, cwd=None, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)


def run_work_flow(work_dir):
    gitbug_java_env = utils.read_json(os.path.join(utils.ROOT_PATH, "Config", "gitbug_java_environment.json"))
    command = (f"cd {gitbug_java_env['gitbug_repo']} && export PATH=\"$(pwd):$(pwd)/bin:$PATH\" "
               f"&& conda run -n {gitbug_java_env['conda_env_name']} gitbug-java run {work_dir}")
    print(command)
    result = subprocess.run(command, shell=True, cwd=None, capture_output=True, text=True, timeout=1200)
    # if result.returncode != 0:
    # print(result.stderr)


def get_init_test_info(working_dir, test_source_dir):
    json_file = os.path.join(working_dir, "gitbug.json")
    data = utils.read_json(json_file)
    test_info = {}
    for run in data.get("actions_runs"):
        if run is None:
            continue
        for testss in run:
            tests = testss["tests"]
            for test in tests:
                if test.get("results")[0].get("result") == "Failure":
                    name = test.get('name')
                    name = refine_test_name(name)
                    test_name = f"{test.get('classname')}::{name}"
                    if test_info.get(test_name) is None:
                        test_info[test_name] = {}
                        test_info[test_name]["test_method"] = test_name
                        if test.get('classname').find("$") != -1:
                            test_info[test_name]["test_case_code"] = utils.get_test_code(
                                working_dir, test_source_dir, test.get('classname')[:test.get('classname').rfind("$")],
                                name)
                        else:
                            test_info[test_name]["test_case_code"] = utils.get_test_code(
                                working_dir, test_source_dir, test.get('classname'), name)
                    if test_info[test_name].get("failing_info") is None:
                        test_info[test_name]["failing_info"] = []
                    message = ""
                    if test.get("results")[0].get("message") is not None:
                        message = test.get("results")[0].get("message")[
                                  :min(200, len(test.get("results")[0].get("message")))]
                    test_info[test_name]["failing_info"].append(message)
    for test, value in test_info.items():
        value["failing_info"] = str(set(value.get("failing_info")))

    return test_info


def match_compile_error(error_message):
    pattern = r"Compilation failure.*?\[ERROR\] (.*?\.java:\[\d+,\d+\].*?)\n.*?\[ERROR\] (.*?)\n"
    matches = re.search(pattern, error_message, re.DOTALL)

    if matches:
        error_message = f"{matches.group(1)}\n{matches.group(2)}"
        print("Compilation failure")
        print(error_message)
        return error_message
    else:
        pattern = r'Task :.*? (\/.*?\.java):(\d+):\s*(error:[^\n]+)'
        matches = re.search(pattern, error_message, re.DOTALL)

        if matches and matches.group(1) is not None and matches.group(2) is not None and matches.group(3) is not None:
            #
            error_message = f"{matches.group(1)}:{matches.group(2)}\n{matches.group(3)}"
            print("Compilation failure")
            print(error_message)
            return error_message
        elif error_message.find("BUILD FAILURE") != -1:
            build_failure_index = error_message.find("BUILD FAILURE")
            relevant_part = error_message[build_failure_index:]

            pattern = r'BUILD FAILURE.*?(\[ERROR\].*?Failed to execute.*?\n.*?)\s*(\S+\.java)'
            match = re.search(pattern, relevant_part, re.DOTALL)

            if match:
                result = f"BUILD FAILURE\n{match.group(1)}{match.group(2).strip()}"
                print(result)
                return result
            else:
                pattern = r'BUILD FAILURE.*?(\[ERROR\].*?Failed to execute.*?\n?.*?)\s*(\S+\.java)'
                match = re.search(pattern, relevant_part, re.DOTALL)

                if match:
                    result = f"BUILD FAILURE\n{match.group(1)}{match.group(2).strip()}"
                    print(result)
                    return result
                else:
                    print("No match found.")
                    return ""
        else:
            print("No match found.")
            return ""


def get_compile_errors(working_dir):
    json_file = os.path.join(working_dir, ".gitbug-java", "test-results.json")
    data = utils.read_json(json_file)
    if data.get("executed_tests") == 0:
        run_output = data.get("run_outputs")[0]
        stdout_str = run_output.get("stdout")
        return False, match_compile_error(stdout_str)
    else:
        run_output = data.get("run_outputs")[0]
        stdout_str = run_output.get("stdout")
        if stdout_str.find("Compilation failure") != -1:
            print("Compilation failure")
            return False, match_compile_error(stdout_str)
        else:
            return True, ""


def get_test_info(working_dir, test_source_dir):
    json_file = os.path.join(working_dir, ".gitbug-java", "test-results.json")
    data = utils.read_json(json_file)
    failed_tests = data.get("failed_tests")

    if len(failed_tests) == 0:
        return 0, {}
    run_output = data.get("run_outputs")[0]
    stdout_str = run_output.get("stdout")
    for failed_test in failed_tests:
        name = f"{failed_test.get('classname')}.{failed_test.get('name')}"
        pattern = (
                r"\[ERROR\] " + re.escape(name) +
                r" -- Time elapsed:.*?FAILURE!\n.*?"  # 
                r"([^\n]+)"  #
        )

        match = re.search(pattern, stdout_str, re.DOTALL)
        if match:
            failing_info = match.group(1).strip()
            if failing_info.find("|") != -1:
                failed_test["failing_info"] = failing_info[failing_info.find("|") + 1:]
        else:
            failed_test["failing_info"] = ""
    test_info = {}
    for failed_test in failed_tests:
        name = failed_test.get('name')
        name = refine_test_name(name)
        test_name = f"{failed_test.get('classname')}::{name}"
        if test_info.get(test_name) is None:
            test_info[test_name] = {}
            test_info[test_name]["test_method"] = test_name
        if test_info[test_name].get("failing_info") is None:
            test_info[test_name]["failing_info"] = []
        test_info[test_name]["failing_info"].append(failed_test.get("failing_info"))

    for test, value in test_info.items():
        value["failing_info"] = str(set(value.get("failing_info")))
        if value.get("failing_info") is not None:
            value["failing_info"] = value.get("failing_info")[:min(200, len(value["failing_info"]))]
    if len(test_info) > 30:
        return len(test_info), test_info
    else:
        for test, value in test_info.items():
            class_name = test.split("::")[0]
            if class_name.find("$") != -1:
                value["test_case_code"] = utils.get_test_code(
                    working_dir, test_source_dir, class_name[:class_name.rfind("$")], test.split("::")[1])
            else:
                value["test_case_code"] = utils.get_test_code(
                    working_dir, test_source_dir, class_name, test.split("::")[1])

        return len(test_info), test_info


def init_gitbug_project_structure(bug_id):
    bug_info = utils.read_json(os.path.join(utils.ROOT_PATH, "datasets", "gitbug-java", "bug_pfl.json")).get(bug_id)
    builder = bug_info.get("builder")
    if builder == "maven":
        return (os.path.join("src", "main", "java"), os.path.join(".act-result", bug_id, "target", "classes"),
                os.path.join("src", "test", "java"), os.path.join(".act-result", bug_id, "target", "test-classes"))
    elif builder == "gradle":
        return (os.path.join("src", "main", "java"), os.path.join(".act-result", bug_id, "build", "classes", "java",
                                                                  "main"), os.path.join("src", "test", "java"),
                os.path.join(".act-result", bug_id, "build", "classes", "java", "test"))
    elif builder == "maven-simple":
        return "src", os.path.join(".act-result", bug_id, "target", "classes"), "test", os.path.join(".act-result",
                                                                                                     bug_id, "target",
                                                                                                     "test-classes")
    elif builder == "maven-middle":
        return os.path.join("src", "main"), os.path.join(".act-result", bug_id, "target", "classes"), os.path.join(
            "src", "test"), os.path.join(".act-result", bug_id, "target", "test-classes")

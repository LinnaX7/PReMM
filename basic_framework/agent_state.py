from typing import TypedDict
from enum import Enum

from benchmark.benchmark import Benchmark


class FaultCode(TypedDict):
    fault_method: str
    fault_code: str
    start_line: int
    end_line: int
    fault_lines: list
    fault_analysis: str
    repair_code: str


class FaultFile(TypedDict):
    # fault code Path
    fault_file_path: str
    fault_snippets: list[FaultCode]


class TestCase(TypedDict):
    test_method: str
    test_case_code: str
    failing_info: str


class DataState(TypedDict):
    # query
    query: str
    # fault files
    fault_files: list[FaultFile]
    # failing_info
    failed_test_cases: list[TestCase]
    # repair_code
    repair_code: str
    # repair success
    repair_success: bool


class FaultCodeState(TypedDict):
    file_path: str
    fault_method: str
    fault_code: str
    line_begin: int
    line_end: int
    fault_lines: list[str]
    fault_line_codes: list[str]
    similar_methods: str
    repaired_code: str


class CompileResult(TypedDict):
    compile_success: bool
    compile_info: str


class RepairStateEnum(str, Enum):
    NOT_REPAIRED = "NOT_REPAIRED"
    REPAIR_SUCCESS = "repair_success"
    REPAIR_TEST_SUCCESS = "repair_test_success"
    REPAIR_TEST_FAILED = "repair_test_failed"
    REPAIR_TEST_IMPROVED = "repair_test_improved"
    COMPILE_ERROR = "compile_error"
    COMPILE_SUCCESS = "compile_success"
    REPAIR_EXCEPTION = "repair_exception"
    REPAIR_FAILED = "repair_failed"
    REPAIR_FORMAT_ERROR = "repair_format_error"
    REPAIR_FORMAT_SUCCESS = "repair_format_success"


class FinalRepairResult(TypedDict):
    fault_codes: dict
    repair_result: RepairStateEnum
    failed_test_num: int


class RepairState(TypedDict):
    fault_analysis_result: str
    repair_count: int
    repair_exception: str
    repair_history: str
    repair_result: RepairStateEnum
    prompt_tokens: int
    completion_tokens: int


class AgentState(TypedDict):
    pid: str
    bug_id: str
    database_name: str
    fault_codes: dict
    fault_codes_list: list[dict]
    fault_files: list[str]
    failed_test_cases: list[TestCase]
    related_tests: set
    compile_error_info: str
    relative_suspicious_paths: list
    key_tokens: dict
    repair_state: RepairState
    repair_best: FinalRepairResult
    neighbor_agents: list
    test_cases_prompt: bool
    dependency_analysis_prompt: bool
    similar_codes_prompt: bool
    key_token_mining_prompt: bool
    fault_analysis_success: bool
    bug_benchmark: Benchmark


class MAgentState(TypedDict):
    bug_id: str
    database_name: str
    agent_states: list[AgentState]
    failed_test_cases: dict
    fault_codes_list: list[dict]
    fault_files: list[str]
    repair_result: RepairStateEnum
    merged_agents: dict
    bug_benchmark: Benchmark

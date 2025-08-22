from enum import Enum


class AgentNodeEnum(str, Enum):
    PREPROCESSOR = "preprocessor"
    FAULT_ANALYZER = "fault_analyzer"
    REPAIRER = "repairer"
    MODIFY_AND_COMPILE_CODES = "modify_and_compile_code"
    RECOVER_CODES = "recover_codes"
    TEST_FAILING_CASES = "test_failing_cases"
    TEST_ALL_CASES = "test_all_cases"
    POSTPROCESSOR = "postprocessor"


class MAgentNodeEnum(str, Enum):
    SUSPICIOUS_METHODS_CLUSTERING = "suspicious_methods_clustering"
    PREPROCESSOR = "preprocessor"
    MULTY_REPAIRER = "multi_repairer"
    COMBINE_AND_TEST = "combine_and_test"
    CONTINUE_TO_OVERALL_COMPILE = "continue_to_overall_compile"
    RECOVER_CODES = "recover_codes"
    TEST_ALL_CASES = "test_all_cases"
    POSTPROCESSOR = "postprocessor"

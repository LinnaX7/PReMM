import os

import utils
from benchmark.benchmark import BenchmarkRegistry, Benchmark


@BenchmarkRegistry.register("new-benchmark")
class NewBenchmark(Benchmark):
    def __init__(self, database_name):
        super().__init__(database_name)
        self.database_name = database_name
        self.bug_id = "bug_id"
        self.work_dir = "work_dir"
        self.source_dir = "source_dir"
        self.build_dir = "build_dir"
        self.test_source_dir = "test_source_dir"
        self.test_build_dir = "test_build_dir"
        self.fault_location_file = "fault_location_file"
        self.init_failing_tests = {}

    def checkout(self, bug_id):
        """Checkout the specific bug version from the repository"""
        self.bug_id = bug_id
        self.work_dir = os.path.join("/tmp", bug_id)

        # TODO: Implement repository checkout logic
        # - Clone or checkout the specific bug version
        # - Set up the directory structure

        # TODO: Set these paths according to the project structure
        self.source_dir = "source_dir"  # e.g., src/main/java/
        self.build_dir = "build_dir"  # e.g., target/classes/
        self.test_source_dir = "test_source_dir"  # e.g., src/test/java/
        self.test_build_dir = "test_build_dir"  # e.g., target/test-classes/

        # TODO: The fault location file of the current bug, e.g., `datasets/defects4jv1.2/fault_location/defects4j/chart/1`
        self.fault_location_file = "fault_location_file"

        # TODO: Initialize failing tests by running initial test suite
        self.init_failing_tests = {}  # Format: {"ClassName::methodName": {"failing_info": ..., "test_code": ...}}

    def compile_files(self, files: list):
        """Compile specific files in the project"""
        # TODO: Implement incremental compilation
        # - Should only compile the specified files
        # - Return (success: bool, error_message: str)
        return True, ""

    def compile_project(self):
        """Compile the entire project"""
        # TODO: Implement full project compilation
        # - Should compile both main and test code
        # - Return (success: bool, error_message: str)
        return True, ""

    def test_failed_test_cases(self, failed_test_cases: list):
        """Run specific test cases that previously failed"""
        test_info = {}
        # TODO: Implement targeted test execution
        # - Should only run the specified test cases
        # - Return dict with format:
        #   {
        #       "ClassName::methodName": {
        #           "test_name": ...,
        #           "failing_info": ...,
        #           "test_code": ...
        #       }
        #   }
        return test_info

    def test_project(self):
        """Run all test cases in the project"""
        test_info = {}
        # TODO: Implement full test suite execution
        # - Should run all test cases
        # - Return tuple: (number_of_failing_tests: int, test_info: dict)
        #   where test_info has format:
        #   {
        #       "ClassName::methodName": {
        #           "failing_info": ...,
        #           "test_case_code": ...
        #       }
        #   }
        return 0, test_info

    def get_all_bugs(self):
        """Get list of all available bugs in this dataset"""
        # TODO: Implement bug enumeration
        # - Should return list of all bug IDs available in this dataset
        # - Can read from metadata file or query repository
        return []

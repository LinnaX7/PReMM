import os


class Benchmark:
    def __init__(self, database_name):
        self.database_name = database_name
        self.bug_id = "bug_id"
        self.work_dir = "work_dir"
        self.source_dir = "source_dir"
        self.build_dir = "build_dir"
        self.test_source_dir = "test_source_dir"
        self.test_build_dir = "test_build_dir"
        self.fault_location_file = "fault_location_file"
        self.init_failing_tests = {}
        self.suspicious_methods = []

    def checkout(self, bug_id):
        self.bug_id = bug_id
        self.work_dir = os.path.join("tmp", bug_id)
        # Todo: Complete the following fields with your own implementation
        self.source_dir = "source_dir"  # the source root directory, e.g., src/main/java/
        self.build_dir = "build_dir"  # the build root directory, e.g., target/classes/
        self.test_source_dir = "test_source_dir"  # the test source root directory, e.g., src/test/java/
        self.test_build_dir = "test_build_dir"  # the test build root directory, e.g., target/test-classes/
        self.fault_location_file = "fault_location_file"  # the file path of the fault location file
        self.init_failing_tests = {}    # the initial failing tests, key is test_method in the format of "ClassName::methodName", value is a dict containing the two fields: "failing_info" and "test_code"

    def get_init_failing_tests(self):
        # key is test_method in the format of "ClassName::methodName"
        # value is a dict containing the two fields: "failing_info" and "test_code"
        return self.init_failing_tests

    def get_work_dir(self):
        return self.work_dir

    def get_source_dir(self):
        return self.source_dir

    def get_build_dir(self):
        return self.build_dir

    def get_test_source_dir(self):
        return self.test_source_dir

    def get_test_build_dir(self):
        return self.test_build_dir

    def get_fault_location_file(self):
        return self.fault_location_file

    def compile_files(self, files: list):
        return True, ""

    def compile_project(self):
        return True, ""

    def test_failed_test_cases(self, failed_test_cases: list):
        test_info = {}
        # key is test_method in the format of "ClassName::methodName"
        # value is a dict containing the three fields: "test_name", "failing_info" and "test_code"
        return test_info

    def test_project(self):
        test_info = {}
        # key is test_method in the format of "ClassName::methodName"
        # value is a dict containing the two fields: "failing_info" and "test_case_code"
        # return the number of failing tests, and the failing test info
        return 0, test_info

    def recover_files(self, file_list):
        self.compile_files(file_list)

    def get_all_bugs(self):
        return []

    def get_suspicious_methods(self):
        return self.suspicious_methods

    def get_suspicious_method(self, index):
        return []


class BenchmarkRegistry:
    _registry = {}

    @classmethod
    def register(cls, name):
        def wrapper(benchmark_class):
            cls._registry[name] = benchmark_class
            return benchmark_class

        return wrapper

    @classmethod
    def create_benchmark(cls, dataset):
        benchmark_class = cls._registry.get(dataset)
        if benchmark_class is None:
            # Check for prefixes if exact match not found
            for name, klass in cls._registry.items():
                if dataset.startswith(name):
                    return klass(dataset)
            raise ValueError(f"No benchmark registered for dataset: {dataset}")
        return benchmark_class(dataset)

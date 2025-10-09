import jpype
import utils
import os
import multiprocessing


def program_analysis_with_pfl_working(queue, root_dir, source_dir, class_dir, fault_loc_file, test_names,
                                      test_build_dir):
    try:
        jvm_path = jpype.getDefaultJVMPath()
        javaparser_path = os.path.join(utils.ROOT_PATH, "java_lib", "context-extractor.jar")
        jpype.startJVM(jvm_path, "-ea", "-Djava.class.path=%s" % javaparser_path)
        ProgramAnalysis = jpype.JClass("ProgramAnalysis")
        String = jpype.JClass('java.lang.String')
        programAnalysis = ProgramAnalysis(root_dir, source_dir, class_dir)
        programAnalysis.faultAnalysis(fault_loc_file, jpype.JArray(String)(test_names), test_build_dir)
        signature_method_map = programAnalysis.getSignatureSuspiciousMethodMap()
        # methods_tests_map = programAnalysis.getSuspiciousMethodsToTestsMap()
        methods_tests_map = programAnalysis.getRelatedSuspiciousMethodsToTestsMap()
        methods_test_paths_map = programAnalysis.getSuspiciousMethodsToTestPathsMap()
        queue.put((str(signature_method_map), str(methods_tests_map), str(methods_test_paths_map)))
        # jpype.shutdownJVM()
    except Exception as e:
        queue.put(str(e))
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()


def program_analysis_with_pfl(root_dir, source_dir, class_dir, fault_loc_file, test_names, test_build_dir):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=program_analysis_with_pfl_working, args=(queue, root_dir, source_dir,
                                                                                      class_dir, fault_loc_file,
                                                                                      test_names,
                                                                                      test_build_dir))
    try:
        process.start()
        process.join()
        # signature_method_map, methods_test_map, method_test_path_map = queue.get()
        # return signature_method_map, methods_test_map, method_test_path_map
        result = queue.get()

        if isinstance(result, Exception):
            raise RuntimeError("Program analysis failed") from result
        return result
    finally:
        if process.is_alive():
            process.terminate()
        process.close()


def program_analysis_repository_with_pfl(root_dir, source_dir, class_dir, test_build_dir, initial_failing_tests,
                                         fault_loc_file):
    try:
        signature_method_map, methods_tests_map, method_test_path_map = program_analysis_with_pfl(
            root_dir,
            source_dir,
            class_dir,
            fault_loc_file,
            initial_failing_tests,
            test_build_dir)
        signature_method_map = eval(signature_method_map.strip())
        methods_tests_map = eval(methods_tests_map.strip())
        method_test_path_map = eval(method_test_path_map.strip())
        for fault_code_info in signature_method_map.values():
            fault_code_info['file_path'] = os.path.join(source_dir,
                                                        fault_code_info.get('file_path'))
            fault_code_info['fault_code'] = utils.get_codes_from_file(
                os.path.join(root_dir, fault_code_info['file_path']),
                fault_code_info.get('line_begin'), fault_code_info.get('line_end'))
            fault_code_info['repaired_code'] = fault_code_info['fault_code']
            utils.decode_code_list(fault_code_info['similar_methods'])
            utils.decode_code_list(fault_code_info['fault_line_codes'])
        return signature_method_map, methods_tests_map, method_test_path_map
    except Exception as e:
        raise Exception(str(e))


def program_analysis_without_pfl_working(queue, root_dir, source_dir, class_dir, fault_methods, test_names,
                                         test_build_dir):
    try:
        jvm_path = jpype.getDefaultJVMPath()
        javaparser_path = os.path.join(utils.ROOT_PATH, "java_lib", "context-extractor.jar")
        jpype.startJVM(jvm_path, "-ea", "-Djava.class.path=%s" % javaparser_path)
        ProgramAnalysis = jpype.JClass("ProgramAnalysis")
        String = jpype.JClass('java.lang.String')
        programAnalysis = ProgramAnalysis(root_dir, source_dir, class_dir)
        programAnalysis.faultAnalysis(jpype.JArray(String)(fault_methods), jpype.JArray(String)(test_names),
                                      test_build_dir)
        signature_method_map = programAnalysis.getSignatureSuspiciousMethodMap()
        # methods_tests_map = programAnalysis.getSuspiciousMethodsToTestsMap()
        methods_tests_map = programAnalysis.getRelatedSuspiciousMethodsToTestsMap()
        methods_test_paths_map = programAnalysis.getSuspiciousMethodsToTestPathsMap()
        queue.put((str(signature_method_map), str(methods_tests_map), str(methods_test_paths_map)))
        # jpype.shutdownJVM()
    except Exception as e:
        queue.put(str(e))
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()


def program_analysis_without_pfl(root_dir, source_dir, class_dir, fault_methods, test_names, test_build_dir):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=program_analysis_without_pfl_working, args=(queue, root_dir, source_dir,
                                                                                         class_dir, fault_methods,
                                                                                         test_names,
                                                                                         test_build_dir))
    try:
        process.start()
        process.join()
        # signature_method_map, methods_test_map, method_test_path_map = queue.get()
        # return signature_method_map, methods_test_map, method_test_path_map
        result = queue.get()

        if isinstance(result, Exception):
            raise RuntimeError("Program analysis failed") from result
        return result
    finally:
        if process.is_alive():
            process.terminate()
        process.close()


def program_analysis_repository_without_pfl(root_dir, source_dir, class_dir, test_build_dir, initial_failing_tests,
                                            fault_methods):
    try:
        signature_method_map, methods_tests_map, method_test_path_map = program_analysis_without_pfl(
            root_dir,
            source_dir,
            class_dir,
            fault_methods,
            initial_failing_tests,
            test_build_dir)
        signature_method_map = eval(signature_method_map.strip())
        methods_tests_map = eval(methods_tests_map.strip())
        method_test_path_map = eval(method_test_path_map.strip())
        for fault_code_info in signature_method_map.values():
            fault_code_info['file_path'] = os.path.join(source_dir,
                                                        fault_code_info.get('file_path'))
            fault_code_info['fault_code'] = utils.get_codes_from_file(
                os.path.join(root_dir, fault_code_info['file_path']),
                fault_code_info.get('line_begin'), fault_code_info.get('line_end'))
            fault_code_info['repaired_code'] = fault_code_info['fault_code']
            utils.decode_code_list(fault_code_info['similar_methods'])
        return signature_method_map, methods_tests_map, method_test_path_map
    except Exception as e:
        raise Exception(str(e))


def related_analysis_working(queue, working_dir, source_dir, class_dir, test_names, test_build_dir, fault_file_list):
    jvm_path = jpype.getDefaultJVMPath()
    javaparser_path = os.path.join(utils.ROOT_PATH, "java_lib", "context-extractor.jar")
    jpype.startJVM(jvm_path, "-ea", "-Djava.class.path=%s" % javaparser_path)
    ProgramAnalysis = jpype.JClass("ProgramAnalysis")
    String = jpype.JClass('java.lang.String')
    programAnalysis = ProgramAnalysis(working_dir, source_dir, class_dir)
    related_tests = programAnalysis.getMethodsRelatedTests(jpype.JArray(String)(test_names), test_build_dir,
                                                           jpype.JArray(String)(fault_file_list))
    queue.put([str(item) for item in related_tests])
    # queue.put(list(related_tests))
    jpype.shutdownJVM()


def related_analysis(working_dir, source_dir, class_dir, test_names, test_build_dir, fault_file_list):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=related_analysis_working, args=(queue, working_dir, source_dir, class_dir,
                                                                             test_names, test_build_dir,
                                                                             fault_file_list))
    process.start()
    process.join()
    process.close()
    related_tests = queue.get()
    return related_tests


def key_token_mining_working(queue, file_path):
    jvm_path = jpype.getDefaultJVMPath()
    javaparser_path = os.path.join(utils.ROOT_PATH, "java_lib", "context-extractor.jar")
    jpype.startJVM(jvm_path, "-ea", "-Djava.class.path=%s" % javaparser_path)
    ProgramAnalysis = jpype.JClass("ProgramAnalysis")
    signatures = ProgramAnalysis.signaturesMining(file_path)
    queue.put(str(signatures))
    # queue.put(list(related_tests))
    jpype.shutdownJVM()


def key_token_mining(working_dir, fault_file):
    queue = multiprocessing.Queue()
    file_path = os.path.join(working_dir, fault_file)
    process = multiprocessing.Process(target=key_token_mining_working, args=(queue, file_path))
    process.start()
    process.join()
    process.close()
    signatures = queue.get()
    return signatures

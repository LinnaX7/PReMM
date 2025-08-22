import argparse
import csv
import os
import time

import utils
from basic_framework.main_graph import main_agent
from basic_framework.repair_graph import get_repair_agent
from benchmark.benchmark import BenchmarkRegistry
from logger import Logger


def run_repair_single_bug(max_tries, version_name, dataset, bug_id, benchmark):
    utils.OUTPUT_DIR = "output" + os.sep + utils.MODEL_NAME + os.sep + version_name + os.sep + dataset
    start_time = time.time()
    if not os.path.exists(utils.OUTPUT_DIR):
        os.makedirs(utils.OUTPUT_DIR)
    repair_result_file = (
            utils.OUTPUT_DIR + os.sep + bug_id + os.sep + f'repair_result-{utils.MAX_ITERATIONS}.csv')
    if not os.path.exists(os.path.join(utils.OUTPUT_DIR, bug_id)):
        os.makedirs(os.path.join(utils.OUTPUT_DIR, bug_id))
    elif os.path.exists(repair_result_file):
        print(f"Has already repaired {bug_id}, ending...")
        return
    print(f"Repairing {bug_id}...")
    utils.test_cases_codes_map = utils.load_test_cases_codes_map(dataset, bug_id)

    repair_count = 0
    utils.Repair_Process_Logger = Logger(
        utils.OUTPUT_DIR + os.sep + bug_id + os.sep + f"{bug_id}-{utils.MAX_ITERATIONS}.log")
    try:
        benchmark.checkout(bug_id)
    except Exception as e:
        print(str(e))
        return
    while (not utils.Repair_Result) and repair_count < max_tries:
        main_agent.invoke({'bug_id': bug_id, "database_name": dataset,
                           'failed_test_cases': benchmark.get_init_failing_tests(),
                           'bug_benchmark': benchmark}, {"recursion_limit": 100})
        repair_count += 1
    rows = ["Bug_id", "Repair_Result", "Repair_Attempt_Count", "Repair_Iterative_Count",
            "Last_Input_Prompt_Tokens", "Last_Completion_Tokens", "Total_Input_Prompt_Tokens",
            "Total_Completion_Tokens"]  # time.sleep(20)
    row = [f"{bug_id}", utils.Repair_Result, repair_count, utils.Repair_Iterative_Count, utils.Prompt_Tokens,
           utils.Completion_Tokens, utils.Total_Prompt_Token, utils.Total_Completion_Token]
    with open(repair_result_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(rows)
        writer.writerow(row)
    end_time = time.time()
    utils.Repair_Process_Logger.log(f"Total Time: {end_time - start_time} s.")
    utils.remove_temp_dir(benchmark.get_work_dir())
    utils.output_test_cases_codes_map(dataset, bug_id)
    utils.Repair_Result = False
    utils.Repair_Iterative_Count = 0
    utils.Prompt_Tokens = 0
    utils.Completion_Tokens = 0
    utils.Total_Prompt_Token = 0
    utils.Total_Completion_Token = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="output")
    parser.add_argument("--lang", type=str, default="java")
    parser.add_argument("--dataset", type=str, default="defects4jv1.2",
                        help="Dataset to use, current support: defects4jv1.2, defects4jv2, defects4j-trans, gitbug-java")
    parser.add_argument("--model", type=str, default="Tongyi")
    parser.add_argument("--bug_id", type=str, default="Lang-7")
    parser.add_argument("--few_shot", type=int, default=0)
    parser.add_argument("--chain_length", type=int, default=5)
    parser.add_argument("--total_tries", type=int, default=3)
    parser.add_argument("--max_token", type=int, default=8192)
    parser.add_argument("-f", "--faulty_methods_clustering", help="flag that enable faulty methods clustering.",
                        action="store_true", default=False)
    parser.add_argument("-c", "--context_extraction", help="flag that enable context extraction.",
                        action="store_true", default=False)
    parser.add_argument("-d", "--dual_agent_based_patch_generation",
                        help="flag that dual-agent-based patch generation.",
                        action="store_true", default=False)
    # parser.add_argument("-i", "--invocation_prompt", help="flag that enable invocation chain prompt.",
    #                     action="store_true", default=False)
    # parser.add_argument("-s", "--similar_codes_prompt", help="flag that enable similar codes prompt.",
    #                     action="store_true", default=False)
    # parser.add_argument("-k", "--key_token_prompt", help="flag that enable key token prompt.",
    #                     action="store_true", default=False)
    # parser.add_argument("-t", "--test_cases_prompt", help="flag that enable test cases prompt.",
    #                     action="store_true", default=False)

    args = parser.parse_args()
    utils.MAX_ITERATIONS = args.chain_length
    utils.Enable_FMC = args.faulty_methods_clustering
    utils.Enable_CX = args.context_extraction
    utils.Enable_DualAgent = args.dual_agent_based_patch_generation
    utils.repair_agent = get_repair_agent()
    if utils.MAX_ITERATIONS > 1:
        utils.Test_Case_Prompt = True
    if utils.Enable_CX:
        utils.Invocation_Chain_Prompt = True
        utils.Similar_Codes_Prompt = True
        utils.key_token_prompt = True
    utils.Repair_Result = False
    utils.Repair_Iterative_Count = 0
    utils.Prompt_Tokens = 0
    utils.Completion_Tokens = 0
    utils.Total_Prompt_Token = 0
    utils.Total_Completion_Token = 0
    version_name = utils.get_version_name()

    cur_benchmark = BenchmarkRegistry.create_benchmark(args.dataset)

    if args.bug_id == "all":
        bug_to_be_repaired = cur_benchmark.get_all_bugs()
        for bug in bug_to_be_repaired:
            run_repair_single_bug(args.total_tries, version_name, args.dataset, bug, cur_benchmark)
    else:
        run_repair_single_bug(args.total_tries, version_name, args.dataset, args.bug_id, cur_benchmark)

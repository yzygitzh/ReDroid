import json
import os
import argparse
import subprocess

from utils import java_full4dsm, get_irrelevant_packages, clean_stack_trace

EVENT_METHOD_ENTRY = 40
EVENT_METHOD_EXIT_WITH_RETURN_VALUE = 42

def is_critical(emu_data, real_data, divergence_threshold, ex_package_set):
    """
    Calc whether the return data sequence leads to
    a critical API

    Currently only consider
    0. have something ASIDE FROM ex_package_set
    1. both emu/real UNIQUE return value
    2. emu and real have common prefix >= 1
    """
    emu_stack_trace_set = set(emu_data[0]["stackTrace"])
    real_stack_trace_set = set(real_data[0]["stackTrace"])
    if len(clean_stack_trace(emu_stack_trace_set, ex_package_set)) == 0 or \
       len(clean_stack_trace(real_stack_trace_set, ex_package_set)) == 0:
        return False

    emu_rets = [(x["returnType"], x["returnValue"]) for x in emu_data]
    real_rets = [(x["returnType"], x["returnValue"]) for x in real_data]

    #min_ret_len = min(len(emu_rets), len(real_rets))
    #if min_ret_len > divergence_threshold:
    #    return False

    #common_prefix_len = 0
    #while common_prefix_len < min_ret_len and \
    #      emu_rets[common_prefix_len] == real_rets[common_prefix_len]:
    #    common_prefix_len += 1

    if (len(set(emu_rets)) == 1 and len(set(real_rets)) == 1):
    #if len(set(real_rets)) == 1:
        if (emu_rets[0] != real_rets[0]) and \
           (not (emu_rets[0][0] == "object" and emu_rets[0][1] != 0)) and \
           (not (real_rets[0][0] == "object" and real_rets[0][1] != 0)):
            return True
    #elif 0 < common_prefix_len < min_ret_len:
    #    return True

    return False

def gen_dsm(emu_results, real_results, divergence_threshold, ex_package_set):
    # if is_critical(emu_results) and is_critical(real_results):
    if is_critical(emu_results, real_results, divergence_threshold, ex_package_set):
        return {
            #"returnValue": list([x["returnValue"] for x in real_results]),
            #"emuReturnValue": list([x["returnValue"] for x in emu_results]),
            "returnValue": real_results[0]["returnValue"],
            "emuReturnValue": emu_results[0]["returnValue"],
            "returnType": real_results[0]["returnType"],
            "emuReturnType": emu_results[0]["returnType"],
            #"stackTrace": real_results[0]["stackTrace"],
            "emuStackTrace": emu_results[0]["stackTrace"],
        }
    else:
        return None

def run(config_json_path):
    """
    parse config file
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    monitor_out_dir = os.path.abspath(config_json["monitor_out"])
    output_dir = os.path.abspath(config_json["output_dir"])
    emulator_id = config_json["emulator_id"]
    real_device_id = config_json["real_device_id"]
    divergence_threshold = config_json["divergence_threshold"]

    # get irrelevant classes
    ex_package_set = get_irrelevant_packages(config_json["irrelevant_packages"])

    monitor_result_list = {}
    for device_id in [emulator_id, real_device_id]:
        monitor_result_list[device_id] = [x for x in os.walk(os.path.join(monitor_out_dir, device_id)).next()[2]]

    common_file_set = set(monitor_result_list[emulator_id]) & set(monitor_result_list[real_device_id])
    monitor_result_paths = {}
    for device_id in [emulator_id, real_device_id]:
        monitor_result_paths[device_id] = [os.path.join(monitor_out_dir, device_id, x)
                                           for x in monitor_result_list[device_id]]

    tmp_result_dict = {}

    for common_file_label in common_file_set:
        monitor_result = {}
        for device_id in [emulator_id, real_device_id]:
            monitor_result_path = os.path.join(monitor_out_dir, device_id, common_file_label)
            monitor_result[device_id] = None
            with open(monitor_result_path, "r") as monitor_result_file:
                monitor_result[device_id] = json.load(monitor_result_file)

        if monitor_result[emulator_id] is None or monitor_result[real_device_id] is None:
            print "%s failed" % common_file_label
            continue

        package_name = monitor_result[emulator_id]["package_name"]
        if package_name not in tmp_result_dict:
            tmp_result_dict[package_name] = {
                emulator_id: {},
                real_device_id: {}, # key: method name & signature, value: {returnVal: times}
            }

        # 1. build results according to real/emu
        # 2. build stack trace according to different threads
        for device_id in [emulator_id, real_device_id]:
            thread_stack_trace = {}
            for monitor_item in monitor_result[device_id]["monitor_result"]:
                tid = monitor_item["thread"]
                if tid not in thread_stack_trace:
                    thread_stack_trace[tid] = []

                if monitor_item["eventKind"] == EVENT_METHOD_ENTRY:
                    thread_stack_trace[tid].append(monitor_item["classMethodName"])
                elif monitor_item["eventKind"] == EVENT_METHOD_EXIT_WITH_RETURN_VALUE:
                    reverse_stack_trace = [] + thread_stack_trace[tid]
                    reverse_stack_trace.reverse()
                    reverse_stack_trace_str = ";".join(reverse_stack_trace)

                    trace_method_id = "%s %s %s" % (monitor_item["classMethodName"],
                                                    monitor_item["signature"],
                                                    reverse_stack_trace_str)

                    class_method, para_types, ret_type = java_full4dsm(" ".join(trace_method_id.split()[:2]))
                    while len(thread_stack_trace[tid]):
                        current_frame = thread_stack_trace[tid].pop()
                        if current_frame == class_method:
                            break

                    if trace_method_id not in tmp_result_dict[package_name][device_id]:
                        tmp_result_dict[package_name][device_id][trace_method_id] = {
                            "paraList": para_types,
                            "classMethodName": class_method,
                            "returnData": []
                        }
                    # reverse_stack_trace = []
                    tmp_result_dict[package_name][device_id][trace_method_id]["returnData"].append({
                        "returnValue": monitor_item["returnValue"],
                        "returnType": monitor_item["returnType"],
                        "stackTrace": reverse_stack_trace
                    })

    result_dict = {}
    # use variance-based heuristic algorithm to find critical APIs
    for package_name in tmp_result_dict:
        result_dict[package_name] = []
        common_method_ids = set(tmp_result_dict[package_name][emulator_id].keys()) & \
                            set(tmp_result_dict[package_name][real_device_id].keys())
        for common_method_id in common_method_ids:
            emu_results = tmp_result_dict[package_name][emulator_id][common_method_id]["returnData"]
            real_results = tmp_result_dict[package_name][real_device_id][common_method_id]["returnData"]
            dsm = gen_dsm(emu_results, real_results, divergence_threshold, ex_package_set)
            if dsm is not None:
                dsm["paraList"] = tmp_result_dict[package_name][real_device_id][common_method_id]["paraList"]
                dsm["classMethodName"] = tmp_result_dict[package_name][real_device_id][common_method_id]["classMethodName"]
                result_dict[package_name].append(dsm)

    # output result_dict
    if os.system("mkdir -p %s" % output_dir):
        print "failed mkdir -p %s" % output_dir
        return

    with open(os.path.join(output_dir, "dsm.json"), "w") as output_file:
        json.dump(result_dict, output_file, indent=2)


def parse_args():
    """
    parse command line input
    """
    parser = argparse.ArgumentParser(description="Collect statistics of traces")
    parser.add_argument("-c", action="store", dest="config_json_path",
                        required=True, help="path/to/trace_stat_config.json")
    options = parser.parse_args()
    return options


def main():
    """
    the main function
    """
    opts = parse_args()
    run(opts.config_json_path)
    return


if __name__ == "__main__":
    main()

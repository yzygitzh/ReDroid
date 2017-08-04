import json
import os
import argparse
import subprocess

from utils import java_full4dsm

EVENT_METHOD_ENTRY = 40
EVENT_METHOD_EXIT_WITH_RETURN_VALUE = 42

def run(config_json_path):
    """
    parse config file
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    monitor_out_dir = os.path.abspath(config_json["monitor_out"])
    output_dir = os.path.abspath(config_json["output_dir"])
    emulator_id = config_json["emulator_id"]
    real_device_id = config_json["real_device_id"]

    monitor_result_list = {}
    for device_id in [emulator_id, real_device_id]:
        monitor_result_list[device_id] = [x for x in os.walk(os.path.join(monitor_out_dir, device_id)).next()[2]]

    common_file_set = set(monitor_result_list[emulator_id]) & set(monitor_result_list[real_device_id])
    monitor_result_paths = {}
    for device_id in [emulator_id, real_device_id]:
        monitor_result_paths[device_id] = [os.path.join(monitor_out_dir, device_id, x)
                                           for x in monitor_result_list[device_id]]

    result_dict = {}

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
        if package_name not in result_dict:
            result_dict[package_name] = {
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
                    trace_method_id = "%s %s" % (monitor_item["classMethodName"], monitor_item["signature"])
                    class_method, para_types, ret_type = java_full4dsm(trace_method_id)
                    while len(thread_stack_trace[tid]):
                        current_frame = thread_stack_trace[tid].pop()
                        if current_frame == class_method:
                            break

                    if trace_method_id not in result_dict[package_name][device_id]:
                        result_dict[package_name][device_id][trace_method_id] = []
                    #reverse_stack_trace = [] + thread_stack_trace[tid]
                    #reverse_stack_trace.reverse()
                    reverse_stack_trace = []
                    result_dict[package_name][device_id][trace_method_id].append({
                        "returnValue": monitor_item["returnValue"],
                        "paraList": para_types,
                        "returnType": ret_type,
                        "classMethodName": class_method,
                        "stackTrace": reverse_stack_trace
                    })

    # output result_dict
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

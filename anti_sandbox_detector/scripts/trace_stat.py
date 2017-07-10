import json
import os
import argparse
import subprocess


def run(config_json_path):
    """
    parse config file
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    trace_comparator_out_dir = os.path.abspath(config_json["trace_comparator_out"])
    output_dir = os.path.abspath(config_json["output_dir"])
    trace_result_list = ["%s/%s" % (trace_comparator_out_dir, x) for x in
                         [x for x in os.walk(trace_comparator_out_dir).next()[2]]]

    app_label_set = set()
    thread_diff_set = set()
    trace_diff_set = set()
    result_dict = {}

    for trace_result_path in trace_result_list:
        with open(trace_result_path, "r") as trace_result_file:
            trace_result = json.load(trace_result_file)
            app_label = trace_result_path.split(os.path.sep)[-1][:-len("_0000-00-00_xxxxxx_0000-00-00_yyyyyy.json")]
            trace_label = trace_result_path.split(os.path.sep)[-1][-len("0000-00-00_xxxxxx_0000-00-00_yyyyyy.json"):-len(".json")]
            # count unique apps
            app_label_set.add(app_label)
            # detect unmatched threads
            if len(trace_result["unmatched_threads"]["emulator"]) or \
               len(trace_result["unmatched_threads"]["real_device"]):
                if app_label not in result_dict:
                    result_dict[app_label] = {}
                if trace_label not in result_dict[app_label]:
                    result_dict[app_label][trace_label] = {}
                result_dict[app_label][trace_label]["unmatched_threads"] = trace_result["unmatched_threads"]
                # count unique apps
                thread_diff_set.add(app_label)
            # detect trace differences
            for thread_info in trace_result["matched_threads"]:
                if thread_info["diverge_idx"] < thread_info["max_common_len"] :
                    if app_label not in result_dict:
                        result_dict[app_label] = {}
                    if trace_label not in result_dict[app_label]:
                        result_dict[app_label][trace_label] = {}
                    if "matched_threads" not in result_dict[app_label][trace_label]:
                        result_dict[app_label][trace_label]["matched_threads"] = {}
                    result_dict[app_label][trace_label]["matched_threads"] = thread_info
                    # count unique apps
                    trace_diff_set.add(app_label)

    # output result_dict
    for app_label in result_dict:
        with open("%s%s%s.json" % (output_dir, os.path.sep, app_label), "w") as output_file:
            json.dump(result_dict[app_label], output_file, indent=2)

    print "App num: %d" % len(app_label_set)
    print "Thread-diff num: %d" % len(thread_diff_set)
    print "Trace-diff num: %d" % len(trace_diff_set)



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

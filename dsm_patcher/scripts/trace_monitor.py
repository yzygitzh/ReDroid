from multiprocessing import Process
from threading import Timer

import json
import os
import argparse
import subprocess

from adb import ADBException, ADBConnection
from utils import java_method_convert
from jdwp import JDWPConnection


def get_monitoring_methods(trace_item_list):
    ret_list = []

    for trace_item in trace_item_list:
        fields = trace_item.split()
        if fields[1].endswith(")Z") or\
           fields[1].endswith(")B") or\
           fields[1].endswith(")C") or\
           fields[1].endswith(")S") or\
           fields[1].endswith(")I") or\
           fields[1].endswith(")J"):
            ret_list.append(java_method_convert(trace_item))
    return set(ret_list)


def monitor_func(device_id, apk_path_list, droidbot_out_dir,
                 trace_comparator_out_dir, output_dir, timeout, is_emulator):
    """
    test apks on the assigned vm/device
    """
    for apk_path in apk_path_list:
        apk_file_name = apk_path.split("/")[-1][:-len(".apk")]
        full_output_dir = "%s/%s/%s" % (output_dir, device_id, apk_file_name)
        if os.system("mkdir -p %s" % full_output_dir):
            print "failed mkdir -p %s" % full_output_dir
            continue

        app_droidbot_out_dir = "%s/%s" % (droidbot_out_dir, apk_file_name)

        # get package name by dumpsys_package file name
        package_name = [x for x in os.walk(app_droidbot_out_dir).next()[2]
                        if x.startswith("dumpsys")][0][len("dumpsys_package_"):-len(".txt")]

        # get monitoring method list from trace_comparator_output_dir
        # tid: methods
        monitoring_methods_list = []
        comparator_result_paths = ["%s/%s" % (trace_comparator_out_dir, x)
                                   for x in os.walk(trace_comparator_out_dir).next()[2]
                                   if x.startswith(apk_file_name)]
        for comparator_result_path in comparator_result_paths:
            with open(comparator_result_path, "r") as comparator_result_file:
                comparator_result = json.load(comparator_result_file)

                unmatched_idx = "emulator" if is_emulator else "real_device"
                matched_idx = "emu_api" if is_emulator else "real_api"

                monitoring_methods = set()
                for thread_info in comparator_result["unmatched_threads"][unmatched_idx]:
                    unmatched_methods = get_monitoring_methods(thread_info["api"])
                    monitoring_methods = monitoring_methods.union(unmatched_methods)
                for thread_info in comparator_result["matched_threads"]:
                    if thread_info[matched_idx] is not None:
                        matched_methods = get_monitoring_methods(thread_info[matched_idx])
                        monitoring_methods = monitoring_methods.union(matched_methods)
                monitoring_methods_list.append(sorted(list(monitoring_methods)))
                print len(monitoring_methods_list[-1])

        # intialize ADB
        adb = ADBConnection(device_id)

        # install the app
        print adb.run_cmd(["install", "-r", "-g", apk_path])

        # set debug-app
        print adb.shell(["am", "set-debug-app", "-w", package_name])
        # start app
        print adb.shell(["am", "start", "diff.strazzere.anti/diff.strazzere.anti.MainActivity"])
        # jdwp attach
        app_pid = adb.get_app_pid(package_name)
        print "%s pid=%d" % (package_name, app_pid)
        port = 7335 if is_emulator else 7336
        print adb.forward(app_pid, port)

        jdwp = JDWPConnection("localhost", port, trace=True)
        jdwp.start()

        # event loops
            # fire events
            # jdwp set breakpoints
            # freeze, hack debug detection method, resume until last method
            # jdwp clear breakpoints
            # wait interval seconds

        # jdwp unattach
        jdwp.stop()

        # uninstall the app
        print adb.run_cmd(["uninstall", package_name])

        with open("%s/monitoring_methods.json" % (full_output_dir), "w") as monitoring_methods_file:
            json.dump(monitoring_methods_list, monitoring_methods_file, indent=2)


def run(config_json_path):
    """
    parse config file
    assign work to multiple phases
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    real_device_droidbot_out_dir = os.path.abspath(config_json["real_device_droidbot_out_dir"])
    emulator_droidbot_out_dir = os.path.abspath(config_json["emulator_droidbot_out_dir"])
    trace_comparator_out_dir = os.path.abspath(config_json["trace_comparator_out_dir"])
    output_dir = os.path.abspath(config_json["output_dir"])

    real_device_id = config_json["real_device_id"]
    emulator_id = config_json["emulator_id"]

    apk_dir = os.path.abspath(config_json["apk_dir"])
    apk_path_list = ["%s/%s" % (apk_dir, x) for x in
                     [x for x in os.walk(apk_dir).next()[2] if x.endswith("apk")]]

    timeout = config_json["timeout"]

    # start monitors
    real_device_monitor = Process(target=monitor_func, args=(
        real_device_id, apk_path_list, real_device_droidbot_out_dir,
        trace_comparator_out_dir, output_dir, timeout, False))
    emulator_monitor = Process(target=monitor_func, args=(
        emulator_id, apk_path_list, emulator_droidbot_out_dir,
        trace_comparator_out_dir, output_dir, timeout, True))

    # real_device_monitor.start()
    emulator_monitor.start()

    # real_device_monitor.join()
    emulator_monitor.join()


def parse_args():
    """
    parse command line input
    """
    parser = argparse.ArgumentParser(description="Monitor trace details including return values")
    parser.add_argument("-c", action="store", dest="config_json_path",
                        required=True, help="path/to/trace_monitor_config.json")
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

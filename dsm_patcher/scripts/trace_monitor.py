from multiprocessing import Process
from threading import Timer

import json
import os
import argparse
import subprocess

from utils import ADBException, ADB


def monitor_func(device_id, apk_path_list, droidbot_out_dir,
                 trace_comparator_output_dir, output_dir, timeout):
    """
    test apks on the assigned vm/device
    """
    for apk_path in apk_path_list:
        full_output_dir = "%s/%s/%s" % (output_dir, device_id,
                                        apk_path.split("/")[-1][:-len(".apk")])
        if os.system("mkdir -p %s" % full_output_dir):
            print "failed mkdir -p %s" % full_output_dir
            continue

        print full_output_dir
        print apk_path_list

def run(config_json_path):
    """
    parse config file
    assign work to multiple phases
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    real_device_droidbot_out_dir = os.path.abspath(config_json["real_device_droidbot_out_dir"])
    emulator_droidbot_out_dir = os.path.abspath(config_json["emulator_droidbot_out_dir"])
    trace_comparator_out_dir = os.path.abspath(config_json["trace_comparator_out_dir"])
    real_device_id = os.path.abspath(config_json["real_device_id"])
    emulator_id = os.path.abspath(config_json["emulator_id"])
    output_dir = os.path.abspath(config_json["output_dir"])

    apk_dir = os.path.abspath(config_json["apk_dir"])
    apk_path_list = ["%s/%s" % (apk_dir, x) for x in
                     [x for x in os.walk(apk_dir).next()[2] if x.endswith("apk")]]

    timeout = config_json["timeout"]

    # start monitors
    real_device_monitor = Process(target=monitor_func, args=(
        real_device_id, apk_path_list, real_device_droidbot_out_dir,
        trace_comparator_out_dir, output_dir, timeout))
    emulator_monitor = Process(target=monitor_func, args=(
        emulator_id, apk_path_list, emulator_droidbot_out_dir,
        trace_comparator_out_dir, output_dir, timeout))

    real_device_monitor.start()
    emulator_monitor.start()

    real_device_monitor.join()
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

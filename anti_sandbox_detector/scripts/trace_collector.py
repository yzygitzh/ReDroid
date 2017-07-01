from multiprocessing import Process
from threading import Timer

import json
import os
import argparse
import subprocess


def timeout_func(process):
    process.send_signal(subprocess.signal.SIGINT)

def tester_func(device_id, apk_path_list, droidbot_args, output_dir, timeout):
    """
    test apks on the assigned vm/device
    """
    for apk_path in apk_path_list:
        full_output_dir = "%s/%s/%s" % (output_dir, device_id,
                                        apk_path.split("/")[-1][:-len(".apk")])
        if os.system("mkdir -p %s" % full_output_dir):
            print "failed mkdir -p %s" % full_output_dir
            continue
        test_cmd = ("droidbot -d {device_id} -a {apk_path} "
                    "{droidbot_args} -o {output_dir}").format(
                        device_id=device_id,
                        apk_path=apk_path,
                        droidbot_args=" ".join(["%s %s" % (x, droidbot_args[x])
                                                for x in droidbot_args]),
                        output_dir=full_output_dir)
        p = subprocess.Popen(test_cmd.split())
        t = Timer(timeout, timeout_func, [p])
        t.start()
        p.wait()
        t.cancel()

def run(config_json_path):
    """
    parse config file
    assign work to multiple vm/device's
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    emulator_id = config_json["emulator_id"]
    real_device_id = config_json["real_device_id"]

    apk_dir = os.path.abspath(config_json["apk_dir"])
    apk_path_list = ["%s/%s" % (apk_dir, x) for x in
                     [x for x in os.walk(apk_dir).next()[2] if x.endswith("apk")]]

    droidbot_args = config_json["droidbot_args"]
    output_dir = os.path.abspath(config_json["output_dir"])
    timeout = config_json["timeout"]

    # start testers
    emulator_tester = Process(target=tester_func, args=(
        emulator_id, apk_path_list, droidbot_args, output_dir, timeout))
    real_device_tester = Process(target=tester_func, args=(
        real_device_id, apk_path_list, droidbot_args, output_dir, timeout))

    emulator_tester.start()
    real_device_tester.start()

    emulator_tester.join()
    real_device_tester.join()


def parse_args():
    """
    parse command line input
    """
    parser = argparse.ArgumentParser(description="Automatically test apps on both real devices and emulators")
    parser.add_argument("-c", action="store", dest="config_json_path",
                        required=True, help="path/to/trace_collector_config.json")
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

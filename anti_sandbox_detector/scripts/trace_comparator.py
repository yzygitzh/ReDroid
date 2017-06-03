from multiprocessing import Process, Pool

import json
import os
import argparse
import subprocess

def compare_trace(real_device_trace_path, emulator_trace_path, output_dir):
    """
    for apk_path in apk_path_list:
        test_cmd = ("droidbot -d {device_id} -a {apk_path} "
                    "{droidbot_args} -o {output_dir}").format(
                        device_id=device_id,
                        apk_path=apk_path,
                        droidbot_args=" ".join(["%s %s" % (x, droidbot_args[x])
                                                for x in droidbot_args]),
                        output_dir="%s/%s/%s" % (output_dir, device_id,
                                                 apk_path.split("/")[-1][:-len(".apk")]))
        subprocess.call(test_cmd.split())
    """
    print real_device_trace_path, emulator_trace_path, output_dir


def run(config_json_path):
    """
    parse config file
    assign work to multiple vm/device's
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    real_device_droidbot_out_dir = os.path.abspath(config_json["real_device_droidbot_out_dir"])
    emulator_droidbot_out_dir = os.path.abspath(config_json["emulator_droidbot_out_dir"])
    output_dir = os.path.abspath(config_json["output_dir"])
    process_num = config_json["process_num"]

    real_device_apps = [x for x in os.walk(real_device_droidbot_out_dir).next()[1]]
    emulator_apps = [x for x in os.walk(emulator_droidbot_out_dir).next()[1]]
    both_apps = list(set(real_device_apps) & set(emulator_apps))

    # generate trace path pairs for comparing
    pool = Pool(processes=process_num)
    for app_name in both_apps:
        real_device_path = "%s/%s/events" % (real_device_droidbot_out_dir, app_name)
        emulator_path = "%s/%s/events" % (emulator_droidbot_out_dir, app_name)

        real_device_traces = sorted([x for x in os.walk(real_device_path).next()[2]
                                     if x.endswith(".trace")])
        emulator_traces = sorted([x for x in os.walk(emulator_path).next()[2]
                                  if x.endswith(".trace")])

        for x, y in zip(real_device_traces, emulator_traces):
            pool.apply_async(compare_trace, ["%s/%s" % (real_device_path, x),
                                             "%s/%s" % (emulator_path, y), output_dir])

    pool.close()
    pool.join()


def parse_args():
    """
    parse command line input
    """
    parser = argparse.ArgumentParser(description="Compare traces collected from real devices and emulators")
    parser.add_argument("-c", action="store", dest="config_json_path",
                        required=True, help="path/to/trace_comparator_config.json")
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

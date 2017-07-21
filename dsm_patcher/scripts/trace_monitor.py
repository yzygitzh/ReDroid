from multiprocessing import Process
from threading import Timer

import json
import os
import time
import argparse

from adb import ADBException, ADBConnection
from utils import java_method_convert, get_monitoring_methods, extract_method_classes
from jdwp import JDWPConnection, JDWPHelper

def monitor_func(device_id, apk_path_list, droidbot_out_dir,
                 trace_comparator_out_dir, output_dir,
                 timeout, tracing_interval, interval, is_emulator):
    """
    test apks on the assigned vm/device
    """
    for apk_path in apk_path_list:
        apk_label = apk_path.split("/")[-1][:-len(".apk")]
        full_output_dir = "%s/%s/" % (output_dir, device_id)
        if os.system("mkdir -p %s" % full_output_dir):
            print "failed mkdir -p %s" % full_output_dir
            continue

        app_droidbot_out_dir = "%s/%s" % (droidbot_out_dir, apk_label)

        # get package name by dumpsys_package file name
        package_name = [x for x in os.walk(app_droidbot_out_dir).next()[2]
                        if x.startswith("dumpsys")][0][len("dumpsys_package_"):-len(".txt")]

        # get event sequences by droidbot_event.json
        droidbot_events = []
        with open("%s/droidbot_event.json" % app_droidbot_out_dir, "r") as event_file:
            droidbot_events = json.load(event_file)[1:] # skip the first HOME event

        # get monitoring method list from trace_comparator_output_dir
        # tid: methods
        monitoring_methods_list = []
        comparator_result_paths = ["%s/%s" % (trace_comparator_out_dir, x)
                                   for x in os.walk(trace_comparator_out_dir).next()[2]
                                   if x.startswith(apk_label)]
        comparator_result_labels = [x.split("/")[-1][:-len(".json")] for x in comparator_result_paths]
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

        # intialize ADB
        adb = ADBConnection(device_id)

        # install the app, set debug-app and start app
        adb.run_cmd("install -r -g %s" % apk_path)
        adb.shell("am set-debug-app -w %s" % package_name)
        adb.shell("am start %s" % droidbot_events[0]["intent"].split()[-1])

        # adb forward
        app_pid = adb.get_app_pid(package_name)
        print "%s pid=%d" % (package_name, app_pid)
        port = 7335 if is_emulator else 7336
        adb.forward(app_pid, port)

        # jdwp init
        jdwp = JDWPConnection("localhost", port)
        jdwp_helper = JDWPHelper(jdwp)

        # jdwp attach
        jdwp.start()

        trace_result = []

        for event_idx, monitoring_methods in enumerate(monitoring_methods_list):
            print droidbot_events[event_idx]
            # suspend vm for configuration
            jdwp_helper.VirtualMachine_Suspend()
            # prepare classes to listen, and listen to them
            class_list = extract_method_classes(monitoring_methods)
            event_ids = []
            for class_pattern in class_list:
                ent, ext = jdwp_helper.EventRequest_Set_METHOD_ENTRY_AND_EXIT_WITH_RETURN_VALUE(class_pattern)
                event_ids.append(ent)
                event_ids.append(ext)

            # start sampling
            jdwp.plug()
            jdwp_helper.VirtualMachine_Resume()

            # fire event after the first event
            if event_idx > 0:
                droidbot_event = droidbot_events[event_idx]
                if droidbot_event["event_type"] == "touch":
                    adb.shell("input tap %d %d" % (droidbot_event["x"], droidbot_event["y"]))
                elif droidbot_event["event_type"] == "intent":
                    adb.shell(droidbot_event["intent"])
                elif droidbot_event["event_type"] == "key":
                    adb.shell("input keyevent %s" % droidbot_event["name"])

            time.sleep(tracing_interval)

            # stop sampling
            jdwp.unplug()
            time.sleep(interval)
            # clear plugs
            for event_id in event_ids:
                jdwp_helper.EventRequest_Clear(event_id[0], event_id[1])

            trace_result.append(jdwp_helper.parse_cmd_packets(jdwp.get_cmd_packets()))

            with open("%s/%s.json" % (full_output_dir, comparator_result_labels[event_idx]), "w") as trace_result_file:
                json.dump(trace_result[event_idx], trace_result_file, indent=2)

        # jdwp un-attach
        jdwp.stop()

        # uninstall the app
        adb.run_cmd(["uninstall", package_name])

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
    tracing_interval = config_json["tracing_interval"]
    interval = config_json["interval"]

    # start monitors
    real_device_monitor = Process(target=monitor_func, args=(
        real_device_id, apk_path_list, real_device_droidbot_out_dir,
        trace_comparator_out_dir, output_dir,
        timeout, tracing_interval, interval, False))
    emulator_monitor = Process(target=monitor_func, args=(
        emulator_id, apk_path_list, emulator_droidbot_out_dir,
        trace_comparator_out_dir, output_dir,
        timeout, tracing_interval, interval, True))

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

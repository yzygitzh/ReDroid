import json
import os
import argparse
import shutil
import subprocess

# common default items
CONFIG_TIMEOUT = 600
CONFIG_INTERVAL = 10
CONFIG_SLEEP_INTERVAL = 3

# trace_collector_config.json default items
TRACE_COLLECTOR_CONFIG_DROIDBOT_ARGS = {
    "-interval": CONFIG_INTERVAL,
    "-count": 5,
    "-policy": "bfs",
    "-no_shuffle": "",
    "-grant_perm": "",
    "-use_method_profiling": "full",
    "-dont_tear_down": ""
}
TRACE_COLLECTOR_CONFIG_OUTPUT_DIR = "ReDroid_apps_droidbot_out"

# trace_comparator_config.json default items
TRACE_COMPARATOR_CONFIG_OUTPUT_DIR = "ReDroid_trace_comparator_out"

# trace_monitor_config.json default items
TRACE_MONITOR_CONFIG_OUTPUT_DIR = os.path.join("ReDroid_dsm", "monitor")

# dsm_generator_config.json default items
DSM_GENERATOR_CONFIG_DIVERGENCE_THRESHOLD = 10
DSM_GENERATOR_CONFIG_OUTPUT_DIR = os.path.join("ReDroid_dsm", "dsm")

def run(config_json_path):
    """
    parse config file
    """
    config_json = json.load(open(os.path.abspath(config_json_path), "r"))

    emulator_id = config_json["emulator_id"]
    real_device_id = config_json["real_device_id"]
    apk_dir = os.path.abspath(config_json["apk_dir"])
    output_dir = os.path.abspath(config_json["output_dir"])
    jdk_path = os.path.abspath(config_json["jdk_path"])
    android_sdk_path = os.path.abspath(config_json["android_sdk_path"])
    redroid_path = os.path.abspath(config_json["redroid_path"])
    process_num = config_json["process_num"]

    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir)

    # generate config files and call scripts
    # 0. make config dir
    config_dir = os.path.join(output_dir, "configs")
    os.makedirs(config_dir)

    # 1. trace_collector
    trace_collector_config = {
        "emulator_id": emulator_id,
        "real_device_id": real_device_id,
        "apk_dir": apk_dir,
        "timeout": CONFIG_TIMEOUT,
        "droidbot_args": TRACE_COLLECTOR_CONFIG_DROIDBOT_ARGS,
        "output_dir": os.path.join(output_dir, TRACE_COLLECTOR_CONFIG_OUTPUT_DIR)
    }
    config_file_path = os.path.join(config_dir, "trace_collector_config.json")
    with open(config_file_path, "w") as config_file:
        json.dump(trace_collector_config, config_file, indent=2)
    p = subprocess.Popen(["python", os.path.join(redroid_path, "anti_sandbox_detector", "scripts", "trace_collector.py"),
                          "-c", config_file_path])
    p.wait()

    # 2. trace_comparator
    trace_comparator_config = {
        "real_device_droidbot_out_dir": os.path.join(trace_collector_config["output_dir"], real_device_id),
        "emulator_droidbot_out_dir": os.path.join(trace_collector_config["output_dir"], emulator_id),
        "output_dir": os.path.join(output_dir, TRACE_COMPARATOR_CONFIG_OUTPUT_DIR),
        "process_num": process_num,
        "irrelevant_packages": {
            "jars": [
                os.path.join(android_sdk_path, "platforms", "android-24", "android.jar"),
                os.path.join(android_sdk_path, "platforms", "android-24", "data", "layoutlib.jar"),
                os.path.join(android_sdk_path, "platforms", "android-24", "optional", "org.apache.http.legacy.jar"),
                os.path.join(android_sdk_path, "platforms", "android-24", "uiautomator.jar"),
                os.path.join(jdk_path, "jre", "lib", "rt.jar")
            ],
            "names": [
                "com.android.dex",
                "libcore",
                "org.chromium",
                "org.android_x86"
            ],
            "libs": os.path.join(redroid_path, "anti_sandbox_detector", "data", "lib_packages.csv")
        }
    }
    config_file_path = os.path.join(config_dir, "trace_comparator_config.json")
    with open(config_file_path, "w") as config_file:
        json.dump(trace_comparator_config, config_file, indent=2)
    p = subprocess.Popen(["python", os.path.join(redroid_path, "anti_sandbox_detector", "scripts", "trace_comparator.py"),
                          "-c", config_file_path])
    p.wait()

    # 3. trace_monitor
    trace_monitor_config = {
        "real_device_id": real_device_id,
        "emulator_id": emulator_id,
        "real_device_droidbot_out_dir": trace_comparator_config["real_device_droidbot_out_dir"],
        "emulator_droidbot_out_dir": trace_comparator_config["emulator_droidbot_out_dir"],
        "trace_comparator_out_dir": trace_comparator_config["output_dir"],
        "apk_dir": apk_dir,
        "output_dir": os.path.join(output_dir, TRACE_MONITOR_CONFIG_OUTPUT_DIR),
        "tracing_interval": CONFIG_INTERVAL,
        "interval": CONFIG_SLEEP_INTERVAL,
        "timeout": CONFIG_TIMEOUT
    }
    config_file_path = os.path.join(config_dir, "trace_monitor_config.json")
    with open(config_file_path, "w") as config_file:
        json.dump(trace_monitor_config, config_file, indent=2)
    p = subprocess.Popen(["python", os.path.join(redroid_path, "dsm_patcher", "scripts", "trace_monitor.py"),
                          "-c", config_file_path])
    p.wait()

    # 4. dsm_generator
    dsm_generator_config = {
        "emulator_id": emulator_id,
        "real_device_id": real_device_id,
        "monitor_out": trace_monitor_config["output_dir"],
        "output_dir": os.path.join(output_dir, DSM_GENERATOR_CONFIG_OUTPUT_DIR),
        "divergence_threshold": DSM_GENERATOR_CONFIG_DIVERGENCE_THRESHOLD,
        "irrelevant_packages": trace_comparator_config["irrelevant_packages"]
    }
    config_file_path = os.path.join(config_dir, "dsm_generator_config.json")
    with open(config_file_path, "w") as config_file:
        json.dump(dsm_generator_config, config_file, indent=2)
    p = subprocess.Popen(["python", os.path.join(redroid_path, "dsm_patcher", "scripts", "dsm_generator.py"),
                          "-c", config_file_path])
    p.wait()


def parse_args():
    """
    parse command line input
    """
    parser = argparse.ArgumentParser(description="Launch a default workflow of ReDroid")
    parser.add_argument("-c", action="store", dest="config_json_path",
                        required=True, help="path/to/default_workflow_config.json")
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

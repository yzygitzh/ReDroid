# Anti-Sandbox Detector

## Introduction

This folder contains utilities for detecting whether an app has anti-sandbox behaviors, including `trace_collector` and `trace_comparator`.

## Usage

Utilities in `scripts` folder are called with corresponding config files in `configs` folder specified. Config file samples are provided in `configs` folder.

1. scripts/trace_collector.py

        $ python scripts/trace_collector.py -c configs/trace_collector_config.json

    This utility collects runtime traces on emulator and real device. Configured by `trace_collector_config.json`:

        {
            "emulator_id": <emulator's-device-id>,
            "real_device_id": <real-device's-device-id>,
            "apk_dir": <path-to-the-folder-containing-apks>,
            "timeout": <droidbot-timeout-time-in-seconds>,
            "droidbot_args": <droidbot-options-in-key-value-form>,
            "output_dir": <output-directory>
        }

    See `configs/trace_collector_config.json` for example.

2. scripts/trace_comparator.py

        $ python scripts/trace_comparator.py -c configs/trace_comparator_config.json

    This utility compares runtime trace collected. Configured by `trace_comparator_config.json`:

        {
            "real_device_droidbot_out_dir": <path-to-droidbot-output-for-real-device>,
            "emulator_droidbot_out_dir": <path-to-droidbot-output-for-emulator>,
            "output_dir": <output-directory>
            "process_num": <max-process-num-python-can-spawn>,
            "irrelevant_packages": # hint for irrelevant code during comparison
            {
                "jars": <list-of-path-to-irrelevant-jars>
                "names": <list-of-irrelevant-package-names>
                "libs": <path-to-libradar's-lib_packages.csv>
            }
        }

    See `configs/trace_comparator_config.json` for example.

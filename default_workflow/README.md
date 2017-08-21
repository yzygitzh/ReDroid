# Default Workflow of ReDroid

The default workflow does the following things:

1. Run `anti_sandbox_detector/scripts/trace_collector.py` to collect real/emu runtime traces by DroidBot
2. Run `anti_sandbox_detector/scripts/trace_comparator.py` to compare real/emu runtime traces and find out APIs to monitor return values
3. Run `dsm_patcher/scripts/trace_monitor.py` to replay DroidBot tests in step 1 and collect return values of APIS specified in step 2
4. Run `dsm_patcher/scripts/dsm_generator.py` to generate the DSM rule using results from step 3
5. Upload the DSM rule from step 4 to the emulator at `/data/system/ReDroid/dsm.json`
6. Install `app_samples/redroid.apk` (an Xposed module) on the emulator

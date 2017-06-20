# ReDroid

## Introduction

ReDroid is a toolbox for detecting and countering anti-sandbox behaviors in Android apps.

* What is anti-sandbox behavior

    Anti-sandbox behavior implies that an app would check whether it's being run on an real device or an emulator, and have different behaviors on both kinds of platforms. This may be necessary for commercial apps to pretend malicious usage (like cheating in a game) and for malware to escape automatic app analysis and attack most valuable targets.

    Known Android apps equipped with anti-sandbox techniques include Collapse Gakuen 2 (game) and DenDroid (malware).

* How does ReDroid work

    Given an Android app, ReDroid runs it on both real and emulator platforms, collects runtime traces and compares the real traces against emulator traces. Apps equipped with anti-sandbox techniques would have (largely) different behaviors, thus different traces are generated on real and emulator platforms. From that ReDroid detect anti-sandbox behaviors.

## Prerequisites

* Runtime

    1. Python version 2.7
    2. JDK version >= 1.7
    3. Android SDK with `platform_tools` and `tools` directory added to `PATH`
    4. [DroidBot][droidbot] installed to `PATH`
    5. (Optional) Android Studio to compile sample apps in `app_samples`

* Source Code

    1. [AOSP][aosp] branch `android-6.0.1_r77`
    2. [Android x86][andx86] branch `android-x86-6.0-r3`

## Related Repositories

1. [DroidBot][droidbot]: A lightweight test input generator for Android. Used in ReDroid for dynamic testing Android apps.
2. [anti-emulator][anti-emulator]: An emulator detector. One of the sample apps.
3. [DenDroid][dendroid]: An Android Trojan equipped with anti-sandbox techniques. One of the sample apps.
4. [LibRadar][libradar]: A detecting tool for 3rd-party libraries in Android apps. Its 3rd party library package detection results is used for trace comparing in ReDroid.

## Usage

There are mainly three modules in ReDroid: `anti_sandbox_detector`, `app_samples` and `marshmallow_modifications`.
* To simply run dynamic tests and get trace comparing results, one needs `anti_sandbox_detector` only.
* To collect more complete runtime traces and speed up emulator testings, one has to apply modifications specified in `marshmallow_modifications` to AOSP and Android x86 source code, and build custom ROMs for emulator and real device.
* To use sample apps, one has to pull git submodules in `app_samples` and build APKs.

### anti_sandbox_detector

**NOTE: Do check config json contents before using**

1. Run testing script to collect runtime traces on emulator and real device:

    `$ python scripts/trace_collector.py -c configs/trace_collector_config.json`

2. Run analysis script to compare runtime trace collected

    `$ python scripts/trace_comparator.py -c configs/trace_comparator_config.json`

### marshmallow_modifications

This module contains some modifications (mainly the expansion of trace log buffer) on original Android system, providing more complete trace generated while testing. There are modifications for **real device** and **emulator**.

* Real Device

    1. Apply patches in `aosp` folder to [AOSP source][aosp] branch `android-6.0.1_r77`
    2. Select the build target as `user` mode on real device, e.g. `aosp_hammerhead-userdebug`
    3. Build the ROM
    4. Flash the ROM into your device

* Emulator

    1. Apply patches in `android-x86` folder to [Android x86 source][andx86] branch `android-x86-6.0-r3`
    2. Select the build target as `android_x86-eng`
    3. Build the ISO
    4. Create a new Virtual Machine in VirtualBox according to the [official documents][andx86_vb], and do some more settings:

        `$ VBoxManage setextradata <your_vm_name> "CustomVideoMode1" "768x1280x32"`

        `$ VBoxManage modifyvm <your_vm_name> --natpf1 adb,tcp,*,5555,*,5555`
    5. Boot from the ISO in VirtualBox. To enable ADB connection, use

        `$ adb connect localhost:5555`
    6. Push the `houdini.sfs` in `libs` onto `/sdcard/` folder in the VM. Then in ADB shell, run

        `$ enable_nativebridges`

        This is to enable ARM native code support on x86 VM.

### app_samples

Build them and use them. For `anti-emulator` sample, NDK is necessary.

[droidbot]: https://github.com/honeynet/droidbot
[anti-emulator]: https://github.com/yzygitzh/anti-emulator
[aosp]: https://source.android.com/
[andx86]: http://www.android-x86.org/
[dendroid]: https://github.com/yzygitzh/dendroid_apk
[libradar]: https://github.com/pkumza/LibRadar
[andx86_vb]: http://www.android-x86.org/documents/virtualboxhowto
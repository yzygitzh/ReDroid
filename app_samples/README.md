# App Samples

## Introduction

This folder contains some sample apps used by ReDroid.

## Description

1. ReDroid.apk

    The Xposed plugin used by ReDroid system, compiled from `dsm_patcher/app/dsm_patcher` Android Studio project. The plugin reads dsm rules from `/data/system/ReDroid/dsm.json` in Android system, hacking into methods specified in the file.

2. AntiEmulator-debug.apk

    An app with several anti-sandbox techniques equipped. Several new features are added in [a new repo][anti-emulator] compared to [origin version][anti-emulator-origin] to test the capability of ReDroid system.

3. Droidian-debug.apk

    A malware making use of special Android build names (`general`, `google`, etc.) to escape from emulator. [Sample Source][dendroid]

[anti-emulator]: https://github.com/yzygitzh/anti-emulator
[anti-emulator-origin]: https://github.com/strazzere/anti-emulator
[dendroid]: https://github.com/yzygitzh/dendroid_apk

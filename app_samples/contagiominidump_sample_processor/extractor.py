import os
import subprocess
import zipfile

from password import password_scheme1, password_scheme2

ZIP_DIR = "/mnt/EXT_volume/lab_data/malware_dropbox/archives/"
OUT_DIR = "/mnt/EXT_volume/lab_data/malware_dropbox/extracted/"
TMP_DIR = "/mnt/EXT_volume/lab_data/malware_dropbox/extracted/tmp"

zip_paths = ["%s/%s" % (ZIP_DIR, x) for x in os.walk(ZIP_DIR).next()[2]
             if x.endswith("zip")]

os.system("mkdir -p %s" % OUT_DIR)
os.system("mkdir -p %s" % TMP_DIR)

for zip_path in zip_paths:
    os.system("rm -rf %s/*" % TMP_DIR)
    r = os.system("7z e '%s' -p%s -o%s -aoa" % (zip_path, password_scheme1(zip_path), TMP_DIR))
    if r != 0:
        r = os.system("7z e '%s' -p%s -o%s -aoa" % (zip_path, password_scheme2(zip_path), TMP_DIR))
    if r != 0:
        print "Extracing %s failed" % zip_path
        continue
    p = subprocess.Popen(["find", TMP_DIR, "-type", "f"], stdout=subprocess.PIPE)
    filelist = p.communicate()[0].split(os.linesep)[:-1]
    apklist = [x for x in filelist
               # heuristically select apks
               if (x.endswith(".apk") or len(x.split(".")[-1]) >= 5)]
    for apk in apklist:
        if apk.endswith(".apk"):
            os.system("cp '%s' '%s/'" % (apk, OUT_DIR))
        else:
            os.system("cp '%s' '%s/%s.apk'" % (apk, OUT_DIR, apk.split(os.path.sep)[-1]))

os.system("rm -rf %s" % TMP_DIR)

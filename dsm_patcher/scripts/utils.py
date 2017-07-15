import subprocess
import logging
import re


class ADBException(Exception):
    """
    Exception in ADB connection
    """
    pass


class ADB():
    """
    interface of ADB
    """

    def __init__(self, serial):
        """
        initiate a ADB connection from serial no
        the serial no should be in output of `adb devices`
        :param device: instance of Device
        :return:
        """
        self.logger = logging.getLogger("ADB")
        self.cmd_prefix = ["adb", "-s", serial]

    def run_cmd(self, extra_args):
        """
        run an adb command and return the output
        :return: output of adb command
        @param extra_args: arguments to run in adb
        """
        if isinstance(extra_args, str) or isinstance(extra_args, unicode):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            self.logger.warning(msg)
            raise ADBException(msg)

        args = [] + self.cmd_prefix
        args += extra_args

        self.logger.debug("command:")
        self.logger.debug(args)
        r = subprocess.check_output(args).strip()
        self.logger.debug("return:")
        self.logger.debug(r)
        return r

    def shell(self, extra_args):
        """
        run an `adb shell` command
        @param extra_args:
        @return: output of adb shell command
        """
        if isinstance(extra_args, str) or isinstance(extra_args, unicode):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            self.logger.warning(msg)
            raise ADBException(msg)

        shell_extra_args = ["shell"] + extra_args
        return self.run_cmd(shell_extra_args)

    def check_connectivity(self):
        """
        check if adb is connected
        :return: True for connected
        """
        r = self.run_cmd("get-state")
        return r.startswith("device")

    def unlock(self):
        """
        Unlock the screen of the device
        """
        self.shell("input keyevent MENU")
        self.shell("input keyevent BACK")

    def press(self, key_code):
        """
        Press a key
        """
        self.shell("input keyevent %s" % key_code)

    def touch(self, x, y):
        self.shell("input tap %d %d" % (x, y))

def java_method_convert(short_sig):
    basic_type_mapping = {
        "Z": "boolean",
        "B": "byte",
        "C": "char",
        "S": "short",
        "I": "int",
        "J": "long",
        "F": "float",
        "D": "double"
    }
    fields = short_sig.split()
    idx = 1
    array_depth = 0
    parsed_paras = []
    while fields[1][idx] != ")":
        if fields[1][idx] == "L":
            class_end_idx = idx
            while fields[1][class_end_idx] != ";":
                class_end_idx += 1
            parsed_paras.append(fields[1][idx + 1:class_end_idx].replace("/", ".") + array_depth * "[]")
            idx = class_end_idx
        elif fields[1][idx] == "[":
            array_depth += 1
        else:
            parsed_paras.append(basic_type_mapping[fields[1][idx]] + array_depth * "[]")
            array_depth = 0
        idx += 1
    return "%s(%s)" % (fields[0], ",".join(parsed_paras))

import subprocess
import logging
import re


class ADBException(Exception):
    """
    Exception in ADB connection
    """
    pass


class ADBConnection():
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

    def install(self, apk_path):
        return self.run_cmd(["install", "-r", "-g", apk_path])

    def uninstall(self, package_name):
        return self.run_cmd(["uninstall", package_name])

    def set_debug_app(self, package_name):
        return self.shell(["am", "set-debug-app", "-w", package_name])

    def get_app_pid(self, target_package_name):
        ps_out = self.shell(["ps", "-t"])
        ps_lines = ps_out.splitlines()
        for ps_line in ps_lines[1:]:
            fields = ps_line.split()
            pid = int(fields[1])
            package_name = fields[-1]
            if target_package_name == package_name:
                return pid
        return -1

    def forward(self, pid, port):
        return self.run_cmd(["forward", "tcp:%s" % str(port), "jdwp:%s" % str(pid)])

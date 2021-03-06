#!/Users/fabio/envs/py38-serial/bin/python

import os
import sys
from datetime import datetime
from math import ceil
from time import sleep, time

import serial
from tqdm import tqdm
from bullet import Bullet, SlidePrompt, utils, YesNo, Input

PACKAGE_SIZE = 200

END_OF_ITEM = b"!eoi"
END_OF_COMMAND = b"!eoc"


def exit(message):
    if isinstance(message, bytes):
        message = message.decode()
    print(message)
    sys.exit(0)


def loggit(*args):
    if len(args) == 1:
        msg = args[0]
    else:
        msg = str(args)
    log = "{} - {}\n".format(datetime.now(), msg)
    with open("serial.log", "a") as f:
        f.write(log)


def human_readable_size(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


class SDManager:
    def __init__(self):
        self.serial = serial.Serial(self.find_serial_port(), 500000, timeout=1)
        try:
            if not self.wait_for(b"READY!"):
                raise Exception("Device is not ready")
        except serial.serialutil.PortNotOpenError:
            exit("Serial port is not open")
        print("Device is ready!\n")
        self.tree = {"/": None}

    def find_serial_port(self):
        for p in os.listdir("/dev/"):
            if p.startswith("cu.usb"):
                return "/dev/{}".format(p)

    def read_buffer(self, size, timeout=10):
        buffer = b""
        end = time() + timeout
        while len(buffer) < size:
            buffer += self.serial.read()
            if time() > end:
                break
        # print("Buffer: ", buffer)
        loggit(buffer)
        return buffer

    def send_buffer(self, buffer):
        loggit("Send: ", buffer)
        self.serial.write(buffer)

    def wait_for(self, message, timeout=10):
        received = self.read_buffer(size=len(message), timeout=timeout)
        if received == message:
            return True
        else:
            raise exit(f"Wrong message. Expected '{message}' and received '{received}'")
        raise exit(f"'{message}'' timeout")

    def wait_for_awk(self, timeout=20):
        # sleep(0.05)
        self.wait_for(b"awk", timeout=timeout)

    def read_many(self, separator, terminator, timeout=10):
        buffer = b""
        items = []
        end = time() + timeout
        while not buffer.endswith(terminator):
            if time() > end:
                loggit('Exception("read_many timeout.")', buffer)
                raise Exception("read_many timeout.")

            if buffer.endswith(separator):
                items.append(buffer[: -len(separator)])
                loggit(buffer)
                buffer = b""
            buffer += self.serial.read()
        loggit(buffer)
        return items

    def read_until(self, terminator, timeout=10):
        end = time() + timeout
        buffer = b""
        while not buffer.endswith(terminator):
            buffer += self.serial.read()
            if time() > end:
                loggit('Exception("read_until timeout.")', buffer)
                raise Exception("read_until timeout.")
        loggit(buffer)
        return buffer

    def send_file(self, file_path, dst=None):
        with open(file_path, "rb") as f:
            content = f.read()

        filename = os.path.basename(file_path)
        if not dst:
            dst = filename
        elif not dst.endswith(filename):
            dst = f"{dst}/{filename}".replace("//", "/")
        packages = ceil(len(content) / PACKAGE_SIZE)
        last_package = len(content) % PACKAGE_SIZE or PACKAGE_SIZE
        print(f"filename:{dst}!")
        self.send_buffer(f"filename:{dst}!".encode())
        response = self.read_buffer(3)
        if response == b"awk":
            pass
        elif response == b"err":
            error = self.read_until(b"!")
            exit(f"Error: {error.decode()}")

        print(f"Size: {len(content)} bytes")
        print(f"packages:{packages}!")
        self.send_buffer(f"packages:{packages}!".encode())
        self.wait_for_awk()
        print(f"last:{last_package}!")
        self.send_buffer(f"last:{last_package}!".encode())
        self.wait_for_awk()
        self.send_buffer(b"start:")
        self.wait_for_awk()
        for p in tqdm(range(packages), unit="B", unit_scale=PACKAGE_SIZE, colour="green"):
            self.send_buffer(content[p * PACKAGE_SIZE : p * PACKAGE_SIZE + PACKAGE_SIZE])
            self.wait_for_awk()
        sleep(3)
        self.wait_for(b"DONE!", timeout=15)
        print("Finished!")

    def navigate(self, pwd="/"):
        parent = self.tree[pwd]
        self.send_buffer(f"navigate:{pwd}!".encode())
        self.wait_for_awk()
        items = self.read_many(separator=b"!eoi", terminator=END_OF_COMMAND, timeout=15)
        entries = []
        max_size, max_date, max_name = len("size"), len("modified"), len("name")
        for item in items:
            size, date, name, is_file = item.decode().split("!")
            size = human_readable_size(int(size))
            is_file = is_file == "file"
            if not is_file:
                name = f"{name}/"
            entries.append([size, date, name, f"{pwd}{name}", is_file])
            max_size = max(max_size, len(size))
            max_date = max(max_date, len(date))
            max_name = max(max_name, len(name))
        entries.sort(key=lambda x: (x[4], x[3]))
        if parent:
            entries = [["--", "--", "..", parent, False]] + entries
        files = {
            (
                f"{size:>{max_size}}   "
                f"{date:<{max_date}}   "
                f"{name:<{max_name}}   "
                f"{'[DIR]' if not is_file else ''}"
            ): (path, is_file)
            for size, date, name, path, is_file in entries
        }
        cli = Bullet(
            prompt=f"{'Size':<{max_size}}   {'Modified':<{max_date}}   {'Name':<{max_name}}",
            choices=list(files.keys()),
        )
        path, is_file = files[cli.launch()]
        utils.clearConsoleUp(len(files) + 2)
        utils.moveCursorDown(1)
        if not is_file:
            if not path in self.tree:
                self.tree[path] = pwd
            self.navigate(path)
        else:
            cli = Bullet(
                prompt=path,
                choices=[f"\t< Back [{pwd}]", "\tDownload", "\tDelete"],
            )
            option = cli.launch()
            utils.clearConsoleUp(5)
            utils.moveCursorDown(1)
            if option == "\tDownload":
                self.download(path, pwd)
            elif option == "\tDelete":
                self.delete(path, pwd)
            else:
                self.navigate(pwd)

    def delete(self, filepath, pwd):
        cli = YesNo(prompt=f"Are you sure you want to delete {filepath}? ", default="n")
        sure = cli.launch()
        utils.clearConsoleUp(2)
        utils.moveCursorDown(1)
        if sure:
            self.send_buffer(f"delete:{filepath}!".encode())
        self.navigate(pwd)

    def download(self, filepath, pwd):
        filename = os.path.basename(filepath)
        current_path = os.path.dirname(os.path.abspath("__file__"))
        cli = Input(prompt="Save as: ", default=f"{current_path}/{filename}")
        filename = cli.launch()
        utils.clearConsoleUp(2)
        utils.moveCursorDown(1)
        if os.path.exists(filename):
            cli = YesNo(prompt=f"File '{filename}' already exists. Overwrite? ", default="n")
            sure = cli.launch()
            utils.clearConsoleUp(2)
            utils.moveCursorDown(1)
            if not sure:
                self.navigate(pwd)
        self.send_buffer(f"download:{filepath}!".encode())
        self.wait_for_awk()
        size = int(self.read_until(END_OF_ITEM).decode().replace(END_OF_ITEM.decode(), ""))
        with open(filename, "wb") as outfile:
            for b in tqdm(range(size), unit="B", colour="green"):
                outfile.write(self.serial.read())
        self.wait_for(END_OF_COMMAND)
        self.navigate(pwd)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        try:
            print("<Ctrl>+C to exit")
            SDManager().navigate()
        except KeyboardInterrupt:
            print("Bye!")
            sys.exit(0)
    elif len(sys.argv) == 3 and sys.argv[1] in ["--send", "-s"]:
        filename = sys.argv[2]
        SDManager().send_file(filename, None)
    elif len(sys.argv) == 4 and sys.argv[1] in ["--send", "-s"]:
        filename = sys.argv[2]
        dst = sys.argv[3]
        SDManager().send_file(filename, dst)
    else:
        print(
            "Usage:\n"
            "\tsdmanager                      : Navigate the SD card content\n"
            "\tsdmanager -s/--send <filepath> : Send given file to the SD card\n"
            "\tsdmanager -h/--help            : Show this message\n"
        )

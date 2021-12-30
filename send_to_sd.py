#!/usr/bin/env python

import os
import sys
from math import ceil
from time import sleep, time

import serial
from tqdm import tqdm


PACKAGE_SIZE = 200


class SDManager:
    def __init__(self):
        self.serial = serial.Serial(self.find_serial_port(), 500000, timeout=1)
        if self.read_buffer(size=6) != b"READY!":
            raise Exception("Device is not ready")
        print("Device is ready!")

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
        # print("\nBuffer: ", buffer)
        return buffer

    def wait_for(self, message, timeout=10):
        received = self.read_buffer(size=len(message), timeout=timeout)
        if received == message:
            return True
        else:
            raise Exception(f"Wrong message. Expected '{message}' and received '{received}'")
        raise Exception(f"'{message}'' timeout")

    def wait_for_awk(self, timeout=20):
        # sleep(0.05)
        self.wait_for(b"awk", timeout=timeout)

    def send_file(self, file_path):
        with open(file_path, "rb") as f:
            content = f.read()

        filename = os.path.basename(file_path)
        packages = ceil(len(content) / PACKAGE_SIZE)
        last_package = len(content) % PACKAGE_SIZE or PACKAGE_SIZE
        print(f"filename:{filename}!")
        self.serial.write(f"filename:{filename}!".encode())
        self.wait_for_awk()
        print(f"Size: {len(content)} bytes")
        print(f"packages:{packages}!")
        self.serial.write(f"packages:{packages}!".encode())
        self.wait_for_awk()
        print(f"last:{last_package}!")
        self.serial.write(f"last:{last_package}!".encode())
        self.wait_for_awk()
        self.serial.write(b"start:")
        self.wait_for_awk()
        for p in tqdm(range(packages), unit="B", unit_scale=PACKAGE_SIZE, colour="green"):
            self.serial.write(content[p * PACKAGE_SIZE : p * PACKAGE_SIZE + PACKAGE_SIZE])
            self.wait_for_awk()
        sleep(3)
        self.wait_for(b"DONE!", timeout=15)
        print("Finished!")


if __name__ == "__main__":
    filename = sys.argv[1]
    SDManager().send_file(filename)

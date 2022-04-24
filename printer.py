import serial
import re
import datetime

skip_list = ("echo:busy: processing", "LCD status", "SILENT MODE", "0 step", "tmc2130", "File selected",
             "echo:enqueing", "echo:Now fresh", "LA10C", "echo:Advance K", "K out of allowed range")


class Printer:
    path = ""
    ser = None
    name = ""
    hotend_temp = "0"
    bed_temp = "0"
    current_file = ""
    progress = "0"
    remaining = "0"
    state = "not connected"
    last_check = datetime.datetime.now()

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.ser = serial.Serial()

    def process(self):
        if self.state == "not connected":
            try:
                self.ser = serial.Serial(self.path, baudrate=115200, timeout=10)
                self.state = "idle"
            except serial.SerialException:
                #print("couldn't open port {:s}".format(self.path))
                self.state = "not connected"
                return

        try:
            while self.ser.in_waiting > 0:
                line = self.ser.readline().decode("utf-8").strip()
                self.process_line(line)
            if (datetime.datetime.now() - self.last_check).seconds > 30:
                self.last_check = datetime.datetime.now()
                self.ser.write(b"M73\r\n")
                self.process_line(self.ser.readline().decode("utf-8").strip())
                self.ser.write(b"M105\r\n")
                self.process_line(self.ser.readline().decode("utf-8").strip())

        except OSError:
            self.state = "not connected"
            print("Connection to Printer {:s} lost!".format(self.name))

    def get_status(self):
        ret = "{:s}: {:s}".format(self.name, self.state)
        if self.state == "not connected":
            return ret
        ret += ", Hotend {:s}°C, Bed {:s}°C".format(self.hotend_temp, self.bed_temp)
        if self.state == "idle":
            return ret
        ret += ", file: {:s}, progress {:s}%, {:s} minutes remaining ".format(self.current_file, self.progress, self.remaining)
        return ret

    def process_line(self, l):
        if l.startswith(skip_list) or l == "ok":
            return
        temp = re.match(".*T:(\d+\.\d).* B:(\d+\.\d)", l)
        if temp:
            self.hotend_temp = temp[1]
            self.bed_temp = temp[2]
            return
        else:
            temp = re.match("T:(\d+\.\d) .*", l)
            if temp:
                self.hotend_temp = temp[1]
                return

        prog = re.match("(NORMAL|T) MODE: Percent done: (.+); print time remaining in mins: (.+); Change.*", l)
        if prog:
            if self.remaining != prog[3]:
                self.state = "printing"
            self.progress = prog[2]
            self.remaining = prog[3]
            if prog[2] == "100" or prog[2] == "-1":
                self.state = "idle"
                self.current_file = ""
            return
        file = re.match("File opened: (.*) Size: (\d+)", l)
        if file:
            self.current_file = file[1]
            self.state = "printing"
            return
        if l.startswith("// action:paused"):
            self.state = "paused"
            return
        if l.startswith("// action:resumed"):
            self.state = "printing"
            return
        if l.startswith("Done printing file"):
            self.state = "idle"
            return
        if l.startswith("echo:enqueing \"CRASH_DETECTED"):
            self.state = "crash"
            return
        if l.startswith("echo:enqueing \"CRASH_RECOVER"):
            self.state = "printing"
            return
        if l.startswith("echo:busy: paused for user"):
            self.state = "waiting for user"
            return
        print("{:s}: unrecognized line: {:s}".format(self.name, l))

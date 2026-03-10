import serial
import time

ser = serial.Serial("COM4", 115200, timeout=0.2)
time.sleep(2)

while ser.in_waiting:
    print(ser.readline().decode(errors="ignore").strip())

commands = [
    "ENABLE",
    "DIR 0",
    "SET_SPEED 2000",
    "STATUS",
]

for cmd in commands:
    print(">", cmd)
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)

time.sleep(3)

for cmd in [
    "SET_SPEED 600",
    "STATUS",
]:
    print(">", cmd)
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)

time.sleep(3)

for cmd in [
    "STOP",
    "DIR 1",
    "SET_SPEED 3000",
]:
    print(">", cmd)
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)

time.sleep(3)

for cmd in [
    "STOP",
    "DISABLE",
    "STATUS",
]:
    print(">", cmd)
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)

end = time.time() + 3
while time.time() < end:
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print("<", line)
    time.sleep(0.02)

ser.close()
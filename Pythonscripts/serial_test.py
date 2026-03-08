import serial
import time

ser = serial.Serial("COM4", 115200, timeout=1)
time.sleep(2)

commands = [
    "ENABLE",
    "DIR 0",
    "STEP 2000",
    "DIR 1",
    "STEP 2000",
    "DISABLE",
]

for cmd in commands:
    print("Sending:", cmd)
    ser.write((cmd + "\n").encode())
    time.sleep(5.0)

    while ser.in_waiting:
        print(ser.readline().decode(errors="ignore").strip())

ser.close()
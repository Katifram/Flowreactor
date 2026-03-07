import serial
import time

PORT = "COM4"
BAUD = 115200

def read_all(ser, duration=1.0):
    end = time.time() + duration
    while time.time() < end:
        while ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(f"< {line}")
        time.sleep(0.05)

def send(ser, cmd: str, wait=0.5):
    print(f"> {cmd}")
    ser.write((cmd + "\n").encode())
    ser.flush()
    read_all(ser, wait)

ser = serial.Serial(PORT, BAUD, timeout=1)

print("Waiting for board reset...")
time.sleep(4)          # give Marlin time to finish booting
read_all(ser, 2.0)     # read startup text completely

send(ser, "M17", 1.0)      # enable motors
send(ser, "M114", 1.0)     # current position
send(ser, "G91", 0.5)      # relative mode
send(ser, "G1 X1000 F3000", 20.0)
send(ser, "M114", 1.0)
send(ser, "M18", 0.5)

ser.close()
print("Done.")
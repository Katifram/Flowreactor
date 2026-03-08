import serial
import time

PORT = "COM4"
BAUD = 115200

def wait_for_ok(ser, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(f"< {line}")
                if line.lower() == "ok":
                    return True
        else:
            time.sleep(0.02)
    return False

def send(ser, cmd: str, timeout=5.0):
    print(f"> {cmd}")
    ser.write((cmd + "\n").encode())
    ser.flush()
    ok = wait_for_ok(ser, timeout=timeout)
    if not ok:
        print(f"< timeout waiting for ok after: {cmd}")

ser = serial.Serial(PORT, BAUD, timeout=1)

print("Waiting for board startup...")
time.sleep(4)

# drain startup text
start = time.time()
while time.time() - start < 2:
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print(f"< {line}")
    time.sleep(0.02)

send(ser, "M17")        # enable motors
send(ser, "M211 S0")    # disable software endstops
send(ser, "G90")        # absolute positioning
send(ser, "G92 X0")     # tell Marlin: current position is X=0
send(ser, "M114")       # report current position

send(ser, "G1 X500 F4000", timeout=10.0)
send(ser, "M400", timeout=10.0)
send(ser, "M114")

send(ser, "G1 X0 F4000", timeout=10.0)
send(ser, "M400", timeout=10.0)
send(ser, "M114")

send(ser, "M18")
ser.close()

print("Done.")
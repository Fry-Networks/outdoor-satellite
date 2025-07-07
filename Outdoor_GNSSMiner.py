"""
Satellite Miner ver. 2.0.1
"""

import serial
import datetime
import os
import pysftp
import json
from cryptography.fernet import Fernet
import uuid
import serial.tools.list_ports
from time import sleep
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import requests
import schedule
import psutil

url = 'https://airback.frynetworks.com/api/submitHDMiner'
alreadyTriedPorts = []


def find_available_serial_port():
    available_ports = list(serial.tools.list_ports.comports())
    print("available_ports:", available_ports)
    for port, desc, hwid in available_ports:
        print("port:", port, "desc :", desc, "hwid :", hwid)
        if "usb" in str(hwid).lower() and (port not in alreadyTriedPorts):
            return port
    return None


def open_serial_connection(port, baudrate=9600, timeout=1):
    print("Opened serial port:", port)
    try:
        print("Opened serial port:", baudrate)
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        return ser
    except serial.SerialException:
        return None

def read_miner_key():
    miner_key_file = f"minerkey.txt"
    with open(miner_key_file, 'r') as f:
        lines = f.read().splitlines()
    return ''.join(lines)

# Function to decrypt config file
def owen_decrypt(key, ciphertext):
    nonce, ct = ciphertext[:16], ciphertext[16:]
    cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ct) + decryptor.finalize()
    return plaintext


def decrypt_config():
    dlt = b'\tc#t\xd8r\x0c\x8aw\xe56\xb4\xadun\x03\xb4d\x93\xccG\x80u\x12\xe7\x81\\\xf5\x8c\xbf*\xa9'
    dlp = b"\x0cD\xce4i.F\x9c\x9f'W\xab\n\xa6\xa5\x0c\xbe)\x13+E\xf9?\x86;!#8\x01\x14\xed\xba}|I\x13g\x01$\xb1\x9eNVc\xdd\xff\x12\xb6\xa2&'\x83\x19CL-\xa2\xdbI\xe9"
    knt = b"\x10'\xe5\xe7o\x19\x83\x9a\x94\x9dyh\xab\xd7\x83\x1e\xc2\xb8\x07\xfe_\x08\xa4\xd0;x\xf7\xbf)C\x1c\xc9"
    knp = b"\x98\xf2\xd8l\xe3\xa3\x92\x95Z\xdfY\x04j\x9b}G\xd0\x83\x1c\x8bi\xa3]!\xd9\x9cM\x99Pq\xdb\x80\xd7.\x9b\xed\xba\xe9\x9fI)i\xd8syy\xabqa\x1f\xf4\xa9\t\x92\xf40Z\xae\x8b\xf3\xe6\xb9\xb1o.?\xde\x85\x155\xeb,m\xd5\xa02Zv\xdaP\xb4\xb4+\xa5t\xb9_\x84\xf4q\xbdmqf\xc4\xcd=Uh\xe2\xb8v\xbbb\xe7s]\xe3\xc6\xbf\xe7\xb9\xbc\x0e\xdd\x02\xd3\xd6\x16\x92\x17\xdf9(\x1c\x0f\x0b\x1f6\x0cMx\xc0R\xe6\xfcu\x02\x0c\xdf/i\xce_\xd4\xd5\x07[`\x16\xec@\xf5\x81\x8a5S$\xe3\\CO\xf3\xcc\xcf\x9e\xa3=\xd5\x9d\x92B\xc9{\xdcI\x16\x91e\xae\xed\x1bh\x98Sas<\xf6\xa0\xb3U\xc9(M\x1b\xa4n\x88\xe0\xf5N\x8c\xd0\x9b\xba[L\xf8Fp\xd0\x04\x9b\xe5,\xf2\xb0\x84%\xcc\xa2\xc4\x16\x98P\xf6\xc3\xfa\x9cU\xf8\x8f\xffj\xad\x12)\x8f\xdb\xc6H9\x92\x08h\x8a\x1dR}\xaa\xa8\xe6A\xf8/\x15\x12\xed{\xa3@N;\xc5\xca\x15\x02\x0c\xca\x10\x86o \x9aT&G\x90'\x0c\x18l4k(2\x1c\x0f\xe0\xf6\x87%\xfe\xdb\xe0\xd0\xb9\x1e:?1\x98\xb1rRh\xb8"
    kas = owen_decrypt(dlt, dlp)
    cipher = Fernet(kas)
    ec = owen_decrypt(knt, knp)
    config = json.loads(cipher.decrypt(ec))
    return config

mac_list = []
miner_key = read_miner_key()
config = decrypt_config()
# config_port = config['serial_port']
config_port = find_available_serial_port()
ports = serial.tools.list_ports.comports()
# ser = serial.Serial(port="COM4", baudrate=9600, timeout=1)

ser = open_serial_connection(config_port)
# print(f"[!] Could not open port: {config}")
alreadyTriedPorts.append(config_port)


# ser = None

def checkDeviceConnectionAndAutoConnect():
    global ser
    if ser is None:
        print(f"[!] Could not open port: {config_port}")
        available_port = find_available_serial_port()
        alreadyTriedPorts.append(available_port)

        if available_port:
            print(f"[_] Found available port: {available_port}")
            ser = open_serial_connection(available_port)
        else:
            print("[_] No available serial ports found.")


connectionCheckOK = False
if ser:
    print("[_] port connected.")
    while not connectionCheckOK:
        print("[_] connection check...")
        data = ser.readline().decode('utf-8').strip()
        sleep(1)
        if data:
            print("[_] Received data - validating...")
            samples = ["GPVTG", "GPGGA", "GPGSA", "GPGSV", "GPGLL", "GPTXT", "GPRMC"]
            for sample in samples:
                if sample in data:
                    connectionCheckOK = True
                    break
            if not connectionCheckOK:
                ser = None
                checkDeviceConnectionAndAutoConnect()
        else:
            ser = None
            print("[_] checking other ports...")
            checkDeviceConnectionAndAutoConnect()

# Get MAC address
mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
addrs = psutil.net_if_addrs()
for iface, addr_list in addrs.items():
    for addr in addr_list:
        if addr.family == psutil.AF_LINK:
            mac_list.append(addr.address)

def write_to_log(data, current_file):
    now = datetime.datetime.now()
    with open(current_file, 'a') as f:
        # f.write(f"{now.strftime('%H:%M:%S')} - {data}\n")
        f.write(f"{data}\n")

def upload_to_sftp(current_file):
    remote_filename = f"/home/fryscrypto/outdoor_gnss/{current_file}"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None  # Disable host key checking.
    with pysftp.Connection("23.19.26.198", username="devdoctor", password="wtf.7001",
                           cnopts=cnopts) as sftp:
        sftp.put(current_file, remote_filename)
    os.remove(current_file)

def fetch_data():
    now = datetime.datetime.now()
    last_upload_minute = now.minute
    current_file = f"FRYgnss_{miner_key}_{now.strftime('%m%d%Y_%H%M%S')}.log"

    while True:
        data = ser.readline().decode('utf-8').strip()
        if data:  # if data is not empty
            
            write_to_log(data, current_file)
            now = datetime.datetime.now()

            print(f"[_] Received: {data} {now.minute}")

            if now.minute != last_upload_minute:

                upload_to_sftp(current_file)
                # Convert the log file to a list
                try:
                    body = {
                        'data': miner_key,
                        'deviceMac': mac_list
                    }
                    response = requests.post(url, json=body)

                    if response.status_code == 200:
                        print(response.json())
                    else:
                        print(f"Error: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"An error occurred: {e}")

                current_file = f"FRYgnss_{miner_key}_{now.strftime('%m%d%Y_%H%M%S')}.log"
                break

schedule.every(10).minutes.do(fetch_data)

while True:
    schedule.run_pending()
    sleep(1)
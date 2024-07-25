import os
import time
import csv
import pynmea2
import serial
import subprocess
from datetime import datetime
import asyncio
from bleak import BleakScanner
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import board
import busio
import bluetooth

# serial connection to the GPS module
gps_serial = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)

# I2C interface for the OLED display
i2c = busio.I2C(board.SCL, board.SDA)

# initialize the OLED display
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# update the OLED display
def update_display(lines):
    disp.fill(0)
    image = Image.new('1', (disp.width, disp.height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for i, line in enumerate(lines):
        draw.text((0, i*10), line, font=font, fill=255)
    disp.image(image)
    disp.show()

#  get GPS data
def get_gps_data():
    while True:
        line = gps_serial.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA'):
            msg = pynmea2.parse(line)
            if msg.timestamp:
                return {
                    "time": msg.timestamp.isoformat(),
                    "latitude": msg.latitude,
                    "longitude": msg.longitude,
                    "altitude": msg.altitude,
                    "satellites": msg.num_sats
                }
            else:
                return {
                    "time": "N/A",
                    "latitude": "N/A",
                    "longitude": "N/A",
                    "altitude": "N/A",
                    "satellites": "N/A"
                }

# parse Wi-Fi scan results
def parse_wifi_data(wifi_data):
    wifi_aps = []
    current_ap = {}
    for line in wifi_data.splitlines():
        if "Cell " in line:
            if current_ap:
                wifi_aps.append(current_ap)
                current_ap = {}
            current_ap['Address'] = line.split("Address: ")[1]
        elif "ESSID:" in line:
            current_ap['ESSID'] = line.split("ESSID:")[1].strip('"')
        elif "Channel:" in line:
            current_ap['Channel'] = line.split("Channel:")[1]
        elif "Frequency:" in line:
            current_ap['Frequency'] = line.split("Frequency:")[1]
        elif "Quality=" in line:
            current_ap['Quality'] = line.split("Quality=")[1].split()[0]
            current_ap['Signal level'] = line.split("Signal level=")[1]
        elif "Encryption key:" in line:
            current_ap['Encryption'] = line.split("Encryption key:")[1]
    if current_ap:
        wifi_aps.append(current_ap)
    return wifi_aps

# get Wi-Fi data
def get_wifi_data():
    result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
    return parse_wifi_data(result.stdout)

# get Bluetooth data
def get_bluetooth_data():
    nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True, lookup_class=False)
    bt_devices = []
    for addr, name in nearby_devices:
        bt_devices.append({
            "address": addr,
            "name": name,
            "rssi": '',
            "capabilities": "Misc [BT]",
            "type": "BT"
        })
    return bt_devices

# store unique Wi-Fi AP MAC addresses
unique_wifi_aps = set()

#  loop to collect data
while True:
    gps_data = get_gps_data()
    wifi_aps = get_wifi_data()
    
    # extract MAC addresses and update the set of unique APs
    for ap in wifi_aps:
        unique_wifi_aps.add(ap['Address'])

    unique_wifi_count = len(unique_wifi_aps)
    bt_data = get_bluetooth_data()
    bt_aps = len(bt_data)

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # write CSV for WiGLE
    log_filename = f'wigle_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    with open(log_filename, 'w', newline='') as csvfile:
        # write pre-header
        csvfile.write('WigleWifi-1.6,appRelease=2.78,model=PiZero,release=11.0.0,device=wardriving,display=128x64-OLED,board=PiZero,brand=RaspberryPi,star=Sol,body=3,subBody=1\n')
        
        # write Wi-Fi header
        wifi_fieldnames = ["MAC", "SSID", "AuthMode", "FirstSeen", "Channel", "Frequency", "RSSI", "CurrentLatitude", "CurrentLongitude", "AltitudeMeters", "AccuracyMeters", "RCOIs", "MfgrId", "Type"]
        writer = csv.DictWriter(csvfile, fieldnames=wifi_fieldnames)
        writer.writeheader()
        
        for ap in wifi_aps:
            writer.writerow({
                "MAC": ap['Address'],
                "SSID": ap.get('ESSID', ''),
                "AuthMode": ap.get('Encryption', ''),
                "FirstSeen": timestamp,
                "Channel": ap.get('Channel', ''),
                "Frequency": ap.get('Frequency', '').split()[0] if 'Frequency' in ap else '',
                "RSSI": ap.get('Signal level', ''),
                "CurrentLatitude": gps_data['latitude'],
                "CurrentLongitude": gps_data['longitude'],
                "AltitudeMeters": gps_data['altitude'],
                "AccuracyMeters": '',  # Assuming no accuracy data available
                "RCOIs": '',  # Assuming no RCOIs data available
                "MfgrId": '',  # Assuming no MfgrId data available
                "Type": 'WIFI'
            })
        
        # write Bluetooth header
        bt_fieldnames = ["BD_ADDR", "Device Name", "Capabilities", "First timestamp seen", "Channel", "Frequency", "RSSI", "Latitude", "Longitude", "Altitude", "Accuracy", "RCOIs", "MfgrId", "Type"]
        writer = csv.DictWriter(csvfile, fieldnames=bt_fieldnames)
        writer.writeheader()
        
        for device in bt_data:
            writer.writerow({
                "BD_ADDR": device['address'],
                "Device Name": device['name'],
                "Capabilities": device['capabilities'],
                "First timestamp seen": timestamp,
                "Channel": '0',
                "Frequency": '',
                "RSSI": device['rssi'],
                "Latitude": gps_data['latitude'],
                "Longitude": gps_data['longitude'],
                "Altitude": gps_data['altitude'],
                "Accuracy": '',  
                "RCOIs": '',  
                "MfgrId": '',  
                "Type": device['type']
            })

    # debug
    print(f'Logged data to {log_filename}')

    # update OLED display
    lines = [
        f"Time: {gps_data['time']}",
        f"Lat: {gps_data['latitude']}",
        f"Lon: {gps_data['longitude']}",
        f"Sats: {gps_data['satellites']}",
        f"Unique Wi-Fi APs: {unique_wifi_count}",
        f"BT found: {bt_aps}"
    ]
    update_display(lines)

    # adjust the sleep time as needed
    time.sleep(60)

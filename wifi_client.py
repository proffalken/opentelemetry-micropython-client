import network
import time

class WiFiConnection:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.connect()
    
    def connect(self):
        print("Connecting to WiFi...")
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            time.sleep(1)
        print("Connected to WiFi:", self.wlan.ifconfig())

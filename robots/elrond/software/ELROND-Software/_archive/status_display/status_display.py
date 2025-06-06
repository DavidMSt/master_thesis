# import socket
# import subprocess
# import threading
# import board
# import time
# import digitalio
# from PIL import Image, ImageDraw, ImageFont
# import adafruit_ssd1306
# from subprocess import check_output
# import os
# import re
#
# def getNetworkInformation():
#     try:
#         # Get the username from the /home directory
#         usernames = os.listdir('/home/')
#         username = usernames[0] if usernames else None
#     except Exception:
#         username = None
#
#     try:
#         # Get the hostname of the device
#         hostname = socket.gethostname()
#     except Exception:
#         hostname = None
#
#     try:
#         # Get the SSID of the current Wi-Fi network
#         ssid = subprocess.check_output(['/sbin/iwgetid', '-r']).decode().rstrip()
#         if ssid == '':
#             ssid = None
#     except Exception:
#         ssid = None
#
#     try:
#         # Get the list of IP addresses
#         ip_string = subprocess.check_output(['hostname', '-I']).decode()
#         ips = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ip_string)
#
#         # Separate IPs into local and USB IPs
#         local_ips = [ip for ip in ips if ip.startswith('192.')]
#         usb_ips = [ip for ip in ips if ip.startswith('169.')]
#
#         # Use the first local IP or set to None if not found
#         local_ip = local_ips[0] if local_ips else None
#
#         usb_ips = usb_ips[0] if usb_ips else None
#
#     except Exception:
#         local_ip = None
#         usb_ips = None
#
#     return {
#         "username": username,
#         "hostname": hostname,
#         "ssid": ssid,
#         "local_ip": local_ip,
#         "usb_ip": usb_ips
#     }
#
# def is_internet_reachable():
#     try:
#         # Try to connect to Google's public DNS server to check internet connectivity
#         socket.create_connection(("8.8.8.8", 53), timeout=1)
#         return True
#     except OSError:
#         return False
#
#
# class Display:
#     _thread: threading.Thread
#     width: int
#     height: int
#     address: int
#
#     i2c: board.I2C
#     display: adafruit_ssd1306.SSD1306_I2C
#
#     border_width = 0
#     skip = 2
#     display_found: bool
#
#     lines: list
#     rotation: int
#     internet_status: bool
#
#     def __init__(self, width: int = 128, height: int = 32, address=0x3C, rotation=0):
#         self.width = width
#         self.height = height
#         self.address = address
#         self.rotation = rotation
#
#         self.i2c = board.I2C()  # uses board.SCL and board.SDA
#
#         self.display_found = False
#
#         self.lines = ['Line 1', 'Line 2', 'Line 3']
#
#         # self.font = ImageFont.load_default()
#         self.font = ImageFont.truetype("DejaVuSansMono.ttf", 10)
#
#         self.internet_status = False
#
#         self._thread = threading.Thread(target=self._threadFunction, daemon=True)
#
#     def init(self):
#         ...
#
#     def start(self):
#         self._thread.start()
#
#     # ------------------------------------------------------------------------------------------------------------------
#     def _threadFunction(self):
#
#         while True:
#
#             # Search the Display
#             if not self.display_found:
#                 self.display = self._searchDisplay()
#
#                 if self.display is not None:
#                     self.display_found = True
#                     print("Display Found")
#                 else:
#                     time.sleep(1)
#
#             if self.display_found:
#                 self._updateDisplay()
#                 time.sleep(0.1)
#
#     # ------------------------------------------------------------------------------------------------------------------
#     def _searchDisplay(self):
#         try:
#             display = adafruit_ssd1306.SSD1306_I2C(self.width, self.height, self.i2c, addr=self.address)
#             display.rotate(self.rotation)
#         except Exception:
#             display = None
#
#         return display
#
#     # ------------------------------------------------------------------------------------------------------------------
#     def _clearDisplay(self):
#         self.display.fill(0)
#         self.display.show()
#
#     # ------------------------------------------------------------------------------------------------------------------
#     def _writeLine(self, line_number: int, text: str):
#         self.lines[line_number] = text
#
#     # ------------------------------------------------------------------------------------------------------------------
#     def _updateDisplay(self):
#         image = Image.new("1", (self.width, self.height))
#
#         # Get drawing object to draw on image.
#         draw = ImageDraw.Draw(image)
#
#         # Draw a white background
#         draw.rectangle((0, 0, self.width, self.height), outline=255, fill=255)
#
#         # Draw a smaller inner rectangle
#         draw.rectangle(
#             (self.border_width, self.border_width, self.width - self.border_width - 1,
#              self.height - self.border_width - 1),
#             outline=0,
#             fill=0,
#         )
#
#         # Draw Some Text
#         text = "Hello World!"
#         bbox = self.font.getbbox(text)
#         (font_width, font_height) = bbox[2] - bbox[0], bbox[3] - bbox[1]
#
#         draw.text(
#             (5, self.skip),
#             self.lines[0],
#             font=self.font,
#             fill=255,
#         )
#
#         draw.text(
#             (5, font_height + 2 * self.skip),
#             self.lines[1],
#             font=self.font,
#             fill=255,
#         )
#
#         draw.text(
#             (5, 2 * font_height + 3 * self.skip),
#             self.lines[2],
#             font=self.font,
#             fill=255,
#         )
#
#         # Draw internet connectivity status (circle in the upper-right corner)
#         if self.internet_status:
#             # Draw a filled circle to indicate internet connectivity
#             draw.ellipse((self.width - 10, 0, self.width - 2, 8), outline=255, fill=255)
#         else:
#             # Draw an empty circle with a diagonal line to indicate no internet connectivity
#             draw.ellipse((self.width - 10, 0, self.width - 2, 8), outline=255, fill=0)
#             draw.line((self.width - 10, 0, self.width - 2, 8), fill=255, width=1)
#
#         # Display image
#         try:
#             self.display.image(image)
#             self.display.show()
#         except Exception:
#             self.display_found = False
#             print("Lost Display")
#
#
# class ConnectionStatusDisplay(Display):
#     _connectionThread: threading.Thread
#     _internetThread: threading.Thread
#
#     def __init__(self, width: int = 128, height: int = 32, address=0x3C, rotation=0):
#         super().__init__(width, height, address, rotation)
#
#         self._connectionThread = threading.Thread(target=self._connectionThreadFunction, daemon=True)
#         self._internetThread = threading.Thread(target=self._internetThreadFunction, daemon=True)
#
#     def start(self):
#         self.lines[0] = ''
#         self.lines[1] = ''
#         self.lines[2] = ''
#         super().start()
#         self._connectionThread.start()
#         self._internetThread.start()
#
#     def _connectionThreadFunction(self):
#         while True:
#             network_information = getNetworkInformation()
#
#             self.font = ImageFont.truetype("DejaVuSansMono.ttf", 10)
#             if network_information['hostname'] is not None:
#                 self.lines[0] = f"{network_information['username']}@{network_information['hostname']}"
#             else:
#                 self.lines[0] = ''
#
#             if network_information['ssid'] is not None:
#                 self.lines[1] = f"SSID: {network_information['ssid']}"
#             else:
#                 self.lines[1] = ''
#
#             if network_information['local_ip'] is not None:
#                 ip = network_information['local_ip']
#             elif network_information['usb_ip'] is not None:
#                 ip = network_information['usb_ip']
#             else:
#                 ip = None
#
#             if ip is not None:
#                 self.lines[2] = f"IP: {ip}"
#             else:
#                 self.lines[2] = ''
#
#             time.sleep(0.5)
#
#     def _internetThreadFunction(self):
#         while True:
#             self.internet_status = is_internet_reachable()
#             time.sleep(2)
#
#
# def run_status_display():
#     display = ConnectionStatusDisplay()
#     display.start()
#
#     while True:
#         time.sleep(10)
#
#
# if __name__ == '__main__':
#     run_status_display()
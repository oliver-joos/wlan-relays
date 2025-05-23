# --------------------------------------------------------------------------------------------------
#  @file  ./relay_webserver.py
#
#  @brief  Simple async Webserver for MicroPython esp32
#
#  @author  oliver.joos@hispeed.ch
# --------------------------------------------------------------------------------------------------
#

"""This Webserver controls output pins of an ESP32 DevKit V1 board.

Client example:  curl -v -m 3 -X POST http://<SERVER-IP> --data '{"pin22": false}'
"""

import sys
import time
import json
import errno

import uasyncio
import network
from machine import Pin

try:
    from secrets import secrets
except ImportError:
    print("WLAN name/password are loaded from secrets.py - please add them there!")
    print("Fall back to access-point mode now.")
    secrets = None


HOSTNAME = "relay-server"
LISTEN_IP = "0.0.0.0"
PORT = 80

HTTP_RESPONSE = """\
HTTP/1.1 {status}
Server: {server}
Connection: close

"""

# Map of Pin names to initialized Pin objects
pin_cache = {}


async def handle_request(reader, writer):
    """Handle an incoming HTTP request."""
    headers = {}
    status = None

    print("Receiving request:")
    while True:
        try:
            line = await reader.readline()
            if not line:
                # Connection closed remotely
                raise OSError(errno.ECONNABORTED)
            line = line.decode().rstrip()
            print('  ' + line)
            if line:
                if status is None:
                    # First HTTP line
                    if line.startswith("POST "):
                        status = 200
                    else:
                        status = 404
                else:
                    # HTTP header line
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
                continue

            if status == 200:
                try:
                    length = int(headers["content-length"])
                except (KeyError, ValueError):
                    length = None
                if length:
                    body = (await reader.read(length)).decode()
                    print('  ' + body)
        except OSError:
            status = None
        except Exception as exc:
            sys.print_exception(exc)
            status = 500
        break

    if status is not None:
        # Handle request
        if body:
            props = json.loads(body)
            for pin_name, new_value in props.items():
                try:
                    pin = pin_cache[pin_name]
                except KeyError:
                    pin = pin_cache[pin_name] = Pin(pin_name, Pin.OUT, value=True)
                print(f"Set {pin} to {'high' if new_value else 'low'}")
                pin.value(bool(new_value))
        else:
            pass

        print("Sending response:")
        resp = HTTP_RESPONSE.format(status=status, server=HOSTNAME)
        print('  ' + '\n  '.join(resp.splitlines()))
        await writer.awrite(resp.replace('\n', '\r\n'))

    await writer.aclose()


def main():
    """Setup network interface controller."""
    nic = network.WLAN(network.STA_IF if secrets else network.AP_IF)
    nic.active(False)
    network.hostname(HOSTNAME)
    if secrets:
        # Connect to router
        nic.active(True)
        nic.connect(secrets["ssid"], secrets["password"])
        print(f'Connecting to SSID {secrets["ssid"]}', end="")
        while not nic.isconnected():
            print(".", end="")
            time.sleep(0.5)
        print()
    else:
        # Start as access-point
        nic.config(ssid=HOSTNAME)
        nic.config(security=0)     # 0 = OPEN, 3 = WPA2, 4 = WPA/WPA2
        # nic.config(password="password")
        print(f'Providing a new access-point {HOSTNAME}')
        nic.active(True)
    print(f"My IP address is {nic.ifconfig()[0]}")

    # Start server task
    server_task = uasyncio.start_server(handle_request, LISTEN_IP, PORT)
    loop = uasyncio.get_event_loop()
    loop.create_task(server_task)
    print(f"Listening on {LISTEN_IP}:{PORT}")
    loop.run_forever()


if __name__ == "__main__":
    main()

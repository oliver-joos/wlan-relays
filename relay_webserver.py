# --------------------------------------------------------------------------------------------------
#  @file  ./relay_webserver.py
#
#  @brief  Simple async Webserver for MicroPython esp32
#
#  @author  oliver.joos@hispeed.ch
# --------------------------------------------------------------------------------------------------
#

"""This Webserver controls output pins of an ESP32 DevKit V1 board.

Client example:  curl -v -m 3 -X POST http://<SERVER-IP> --data '{"LED": false}'
"""

import sys
import time
import json
import errno
import os

import uasyncio
import network
from machine import Pin

try:
    from secrets import secrets
except ImportError:
    secrets = None


HOSTNAME = "relay-server"
LISTEN_IP = "0.0.0.0"
PORT = 80
STATIC_DIRPATH = "www/"

# MIME types of common filename extensions
_MIMETYPE_OF_EXT = {
    "html": "text/html",
    "js": "application/javascript",
    "xml": "text/xml",
    "css": "text/css",
    "png": "image/png",
    "jpg": "image/jpg",
    "gif": "image/gif",
    "ico": "image/ico",
    "json": "application/json",
    "txt": "text/plain",
    "log": "text/plain",
    "csv": "text/csv",
}
_MIMETYPE_DEFAULT = "application/octet-stream"

_CACHE_MAX_AGE = const(600)

# Common HTTP status codes and reasons
_STATUS_REASONS = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    500: "Internal Server Error",
}

# Map of Pin names to initialized Pin objects
pin_cache = {}


def guess_mimetype(pathname):
    # Guess MIME type from pathname of a file
    root, ext = pathname.rsplit(".", 1)
    if ext.isdigit():
        # Take name extension without ".<number>"
        root, ext = root.rsplit(".", 1)
    return _MIMETYPE_OF_EXT.get(ext, _MIMETYPE_DEFAULT)


class Response:

    def __init__(self, writer):
        self.writer = writer
        self.headers = {}

    def set_header(self, key, value):
        self.headers[key] = value

    def start_response(self, status=200, content_len=0, content_type=None, gzipped=False):
        print(f"Send HTTP status {status}")
        write = self.writer.write
        reason = _STATUS_REASONS.get(status)
        if reason:
            write(b"HTTP/1.1 %s %s\r\n" % (status, reason))
        else:
            write(b"HTTP/1.1 %s\r\n" % status)
        if content_len is not None:
            write(b"Content-Length: %s\r\n" % content_len)
        if content_len:
            if content_type:
                if content_type.startswith("text/") and "charset=" not in content_type:
                    write(b"Content-Type: %s;charset=utf-8\r\n" % content_type)
                else:
                    write(b"Content-Type: %s\r\n" % content_type)
            if gzipped:
                write(b"Content-Encoding: gzip\r\n")
        for k_v in self.headers.items():
            write(b"%s: %s\r\n" % k_v)
        write(b"Server: %s\r\n\r\n" % HOSTNAME)

    async def sendstream(self, f):
        send_buffer = memoryview(bytearray(1024))
        size = 0
        while True:
            nbytes = f.readinto(send_buffer)
            if not nbytes:
                break
            if nbytes < len(send_buffer):
                piece = send_buffer[:nbytes]
            else:
                piece = send_buffer
            self.writer.write(piece)
            size += nbytes
        await self.writer.drain()
        return size

    async def sendfile(self, fpath, content_type=None, req_headers=None):
        """Send a file as HTTP response to a request.

        If we fail to read the file a response with HTTP status 404 will be sent.
        If there is a request header "Last-Modified" with the mtime of the file then a
        HTTP status 304 (Not Modified) with an empty body will be sent.

        :param fpath:           absolute or relative path of the file
        :param content_type:    content-type of the file, or None to guess it from file name
        :param req_headers:     HTTP headers of the request as dict (e.g. to allow caching)
        :raises OSError:        if an error occurs when opening or reading the file
        """
        error = None
        for ending in (".gz", ""):
            try:
                fpath_ext = fpath + ending
                fstat = os.stat(fpath_ext)
                mtime = str(fstat[8])  # modification time
                self.set_header("Last-Modified", mtime)
                self.set_header("Cache-Control", f"max-age={_CACHE_MAX_AGE}")
                if req_headers.get("if-modified-since") == mtime:
                    # Send status "Not modified"
                    self.start_response(status=304)
                else:
                    with open(fpath_ext, "rb") as f:
                        self.start_response(
                            content_len=fstat[6],
                            content_type=content_type or guess_mimetype(fpath),
                            gzipped=bool(ending)
                        )
                        size = await self.sendstream(f)
                        print(f"Sent {fpath_ext} ({size} bytes)")
                error = None
                break
            except OSError as exc:
                if exc.errno in (errno.ENOENT, errno.EINVAL, errno.EISDIR):
                    error = exc
                    continue
                raise
        if error:
            raise error


async def handle_request(reader, writer):
    """Handle an incoming HTTP request."""
    method = None
    headers = {}
    status = None
    resp = Response(writer)

    print("\nReceiving request:")
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
                    try:
                        method, path = line.rsplit(" ", 3)[-3:-1]
                    except ValueError:
                        status = 400
                    if method in ("GET", "POST"):
                        status = 200
                    else:
                        status = 400
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
        if method == "POST":
            props = json.loads(body)
            for pin_name, new_value in props.items():
                try:
                    pin = pin_cache[pin_name]
                except KeyError:
                    pin = pin_cache[pin_name] = Pin(pin_name, Pin.OUT, value=True)
                print(f"Set {pin} to {'high' if new_value else 'low'}")
                pin.value(bool(new_value))
                resp.start_response(status=200)

        elif method == "GET":
            if path.endswith("/"):
                # Append default filename
                path += "index.html"
            path = STATIC_DIRPATH + path.lstrip("/")
            try:
                await resp.sendfile(path, req_headers=headers)
            except OSError as exc:
                print(f"Failed to access {path}: {exc}")
                resp.start_response(status=404)

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
        print("Cannot read WLAN name/password from secrets.py!")
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

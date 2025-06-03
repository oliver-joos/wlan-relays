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
    304: "Not Modified",
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
        print(f"Sending HTTP status {status}")
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
        """Send a HTTP response with a file in the body.

        If there is a request header "Last-Modified" with the same mtime like the file
        then a HTTP status 304 (Not Modified) with an empty body will be sent.

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
                    # Send status "Not Modified"
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
    method = status = None
    headers = {}
    resp = Response(writer)

    print("\nReceiving HTTP request:")
    try:
        while True:
            line = await reader.readline()
            if not line:
                # Connection closed remotely
                raise OSError(errno.ECONNABORTED)
            line = line.decode().rstrip()
            if not line:
                break
            if status is None:
                # First HTTP line
                print(f'  {line}')
                method, path = line.rsplit(" ", 3)[-3:-1]
                if method not in ("GET", "POST"):
                    status = 400
                    break
                status = 200
            else:
                # HTTP header line
                # print(f'  {line}')
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        if status == 200:
            length = headers.get("content-length")
            if length is not None:
                body = (await reader.read(int(length))).decode()
                print('  ' + body)
    except OSError:
        method = status = None
    except Exception as exc:
        sys.print_exception(exc)
        method = None
        status = 400

    # Handle HTTP method
    if method == "POST":
        try:
            props = json.loads(body)
            for pin_name, new_value in props.items():
                try:
                    pin = pin_cache[pin_name]
                except KeyError:
                    pin = pin_cache[pin_name] = Pin(pin_name, Pin.OUT, value=True)
                print(f"Set {pin} to {'high' if new_value else 'low'}")
                pin.value(bool(new_value))
            status = 200
        except ValueError:
            status = 400

    elif method == "GET":
        if path.endswith("/"):
            # Append default filename
            path += "index.html"
        path = STATIC_DIRPATH + path.lstrip("/")
        try:
            await resp.sendfile(path, req_headers=headers)
            status = None
        except OSError as exc:
            print(f"Failed to access {path}: {exc}")
            status = 404

    if status is not None:
        try:
            # Send HTTP status
            resp.start_response(status)
        except OSError:
            pass

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
        print(f'Connecting to WLAN {secrets["ssid"]} ', end="")
        while not nic.isconnected():
            print(".", end="")
            time.sleep(0.5)
        print()
    else:
        print("Cannot read WLAN ssid/password from secrets.py!")
        # Provide access-point
        nic.config(ssid=HOSTNAME)
        nic.config(security=0)     # 0 = OPEN, 3 = WPA2, 4 = WPA/WPA2
        # nic.config(password="password")
        print(f'Providing new access-point {HOSTNAME}')
        nic.active(True)

    # Run server
    loop = uasyncio.get_event_loop()
    start_task = uasyncio.start_server(handle_request, LISTEN_IP, 80)
    server = loop.run_until_complete(start_task)
    print(f"Listening for http://{nic.ifconfig()[0]}")
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.run_until_complete(server.task)
        print("Server closed")


if __name__ == "__main__":
    main()

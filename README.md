# WLAN Relays

This is a very simple HTTP server written in [MicroPython](https://micropython.org/)
for controlling pins of an ESP32 board. These pins can be connected to solid state
relays to switch lamps for example.

## Client Example

The board will start in access-point mode. This means it provides its own WLAN and you
have to connect your computer or phone to it first. In this mode, the board always has
the **IP address 192.168.4.1**.

Set pin D22 to low using the HTTP client **curl**:

```console
curl -v -m 3 -X POST http://192.168.4.1:7005 --data '{"pin22": false}'
```

You can connect the board to your existing WLAN by entering your WLAN SSID and
password into ``secrets.py``. In this mode, your router assigns a new IP address to the board, which is then displayed in the web interface of most routers.

## The Hardware

**ESP32 DevKit V1** boards have WLAN / Bluetooth built-in and run with 5V and
only 50mA idle or 130mA while transmitting. Pinouts of ESP32 boards are
[here](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/).

A few hundreds of watts AC can be switched with **5V DC AC solid state relays**. Some of these can be controlled directly by 3.3V output pins. During power-up the ESP32 pins are inputs (have high impedance but 3.3V). To keep relays off until the pins are actively controlled as outputs you can choose **Low Level Trigger variants** (>1V ⇒ off, <1V ⇒ on).

## Additional hints

* To reset the ESP32 board press **button "EN"**
* To suppress boot messages pull-down **Pin D15 to GND** with a 10k resistor (helps to avoid problems with terminal tools)
* Pins >=34 are **inputs only!** (no output on D34, D35)

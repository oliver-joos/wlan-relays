# WLAN Relays

This repository contains a very simple HTTP server written in
[MicroPython](https://micropython.org/) for controlling pins of an ESP32 board.
These pins can be connected to solid state relays to switch lamps for example.

## Client Example

The board will start in access-point mode. This means it provides its own WLAN
and you have to connect your computer or phone to it first. In this mode, the
board always has the **IP address 192.168.4.1**.

Set pin D22 to low using the HTTP client **curl**:

```shell
curl -v -m 3 -X POST http://192.168.4.1:7005 --data '{"pin22": false}'
```

You can connect the board to your existing WLAN by entering your WLAN SSID and
password into ``secrets.py``. In this mode, your router assigns a new IP address
to the board, which is then displayed in the web interface of most routers.

## The Hardware

**ESP32 DevKit V1** boards have WLAN hardware built-in and run with 5V and
only 50mA idle or 130mA while transmitting. Pinouts of common ESP32 boards are
[here](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/).

A few hundred watts AC can be switched with a **5V DC AC solid state relay**.
Some of these can be controlled directly by 3.3V output pins. During power-up
the ESP32 pins are inputs (have high impedance but 3.3V). To keep relays off
until the pins are actively controlled as outputs you can use
**Low Level Trigger variants** (>1V ⇒ off, <1V ⇒ on).

### Additional hints

* To reset a ESP32 DevKit V1 board press **button "EN"**
* To suppress boot messages pull-down **Pin D15 to GND** with a 10k resistor
  (helps to avoid problems with terminal tools)
* Pins >=34 are **inputs only!** (no output on D34, D35)

## The Software

The following tutorial works on a Linux Mint 21.x or similar Debian-based Linux
like Ubuntu. You can run Linux Mint directly from a Live USB stick without
installing it on your computer.

Install the **ESP-IDF 5.0.4** build tools (**only needed once!**):

```shell
sudo apt update
sudo apt install git wget flex bison gperf python3 python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0
sudo apt remove brltty                  # stop brltty from stealing /dev/ttyUSBx

mkdir -p ~/esp && cd ~/esp
git clone -b v5.0.4 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32

sudo adduser $USER dialout              # allow access to USB serial devices
# ... and then logout and login again!
```

Download this project and prepare MicroPython for ESP32 (**only needed once!**):

```shell
mkdir -p ~/git && cd ~/git
git clone https://github.com/oliver-joos/wlan-relays.git
cd wlan-relays
git submodule update --init micropython/

make -C micropython/mpy-cross/
make -C micropython/ports/esp32/ submodules
```

Setup your terminal (**needed once per session!**):

```shell
source ~/esp/esp-idf/export.sh
export ESPPORT=/dev/ttyUSB0             # or /dev/ttyACM0 for CH9102X USB ICs
export ESPBAUD=921600
```

Build and deploy the MicroPython firmware image:

```shell
make -C micropython/ports/esp32/ clean  # only after changes in micropython/
make -C micropython/ports/esp32/ -j all

make -C micropython/ports/esp32/ PORT=$ESPPORT erase  # only for empty boards
make -C micropython/ports/esp32/ PORT=$ESPPORT deploy
```

Copy Python files to your board (**overwrites existing files!**):

```shell
./micropython/tools/mpremote/mpremote.py fs cp *.py :/
```

Now press the reset button on your board!

To see log messages or soft-reset the board you can use the MicroPython REPL interface:

```shell
./micropython/tools/mpremote/mpremote.py    # connect to REPL

# press Ctrl+C to abort the application
# press Ctrl+D to soft-reset the system
# press Ctrl+X to exit the mpremote tool
```

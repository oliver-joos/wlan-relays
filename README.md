# WLAN Relays

This repository contains a simple HTTP server written in
[MicroPython](https://micropython.org/) for controlling the pins of ESP32 boards.
These pins can be connected to solid-state relays to switch devices such as lamps.

## Usage

First the board starts in **access-point mode**, which means it creates its own
WLAN network. You must connect your computer or phone to this network.
In this mode, the board always has the **IP address 192.168.4.1**.

To set the LED pin to low using the HTTP client **curl**, use the command:

```shell
curl -v -m 3 -X POST http://192.168.4.1 --data '{"LED": false}'
```

You can connect the board to your existing WLAN by entering your WLAN SSID and
password into the `secrets.py` file. In this mode, your router assigns a new IP
address to the board, which can be viewed in the Web interface of most routers.
The board also announces its hostname as **relay-server**. If your router
supports this, you can access the board using its hostname:

```shell
curl -v -m 3 -X POST http://relay-server.local --data '{"RELAY4": true}'
```

This HTTP server can also host Web pages stored in the `www/` directory.
The current example provides a single button to toggle the LED pin.
You can access the `www/index.html` page with any browser at
<http://relay-server.local/index.html>.

## The Hardware

ESP32 boards come with built-in WLAN hardware and operate at 5V and
only 50mA in idle mode or 130mA while transmitting.

You can find pinouts for common ESP32 boards
[here](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/).
Valid pin names can be found in the `pins.csv` file located in the
corresponding boards directory.

A **5V DC AC solid-state relay** can switch a few hundred watts of AC power.
Some of these relays can be controlled directly by 3.3V output pins.
During power-up the ESP32 pins are inputs (high impedance but at 3.3V).
To keep the relays off until the pins are actively controlled as outputs,
you can use **Low Level Trigger variants** (where >1V ⇒ off and <1V ⇒ on).

### Additional Hints

* To reset an ESP32 DevKit V1 board, press the **"EN" button**
* To suppress boot messages, pull down **Pin D15 to GND** using a 10k resistor
  (helps avoid issues with data transfer tools)
* Pins numbered 34 and above are **input-only!** (no output on D34, D35)

## The Software

The following tutorial has been tested on Linux Mint 21.3. It should also work
on newer Mint or similar Debian-based distributions like Ubuntu. You can run
Linux directly from a Live USB stick without installing it on your computer.

Install the **ESP-IDF 5.4.1** build tools (**only needed once!**):

```shell
sudo apt update
sudo apt install git wget flex bison gperf python3 python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0
sudo apt remove brltty  # stop brltty from stealing /dev/ttyUSBx

mkdir -p ~/esp && cd ~/esp
git clone -b v5.4.1 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32

sudo adduser $USER dialout  # allow access to USB serial devices
# ... then log out and back in!
```

Download this project and prepare MicroPython for ESP32 (**only needed once!**):

```shell
mkdir -p ~/git && cd ~/git
git clone https://github.com/oliver-joos/wlan-relays.git
cd wlan-relays
git submodule update --init micropython/

make -C micropython/mpy-cross/  # build the MicroPython cross-compiler
```

Setup your terminal (**needed once per session!**):

```shell
source ~/esp/esp-idf/export.sh  # activate virtual environment for ESP tools

# Choose your board:
export BOARD=ESP32_DEVKIT ;       export ESPPORT=/dev/ttyACM0
export BOARD=ESP32_LOLIN32_LITE ; export ESPPORT=/dev/ttyUSB0
export BOARD=ESP32_C3_SUPERMINI ; export ESPPORT=/dev/ttyACM0

export BOARD_DIR=$PWD/boards/$BOARD
export ESPBAUD=921600
```

Build and deploy the MicroPython firmware image:

```shell
make -C micropython/ports/esp32/ submodules  # update necessary submodules

make -C micropython/ports/esp32/ BOARD_DIR=$BOARD_DIR clean  # only after changes in micropython/
make -C micropython/ports/esp32/ BOARD_DIR=$BOARD_DIR -j all

make -C micropython/ports/esp32/ BOARD_DIR=$BOARD_DIR erase  # only for empty boards
make -C micropython/ports/esp32/ BOARD_DIR=$BOARD_DIR deploy
```

Copy Python and www files to your board (**overwrites existing files!**):

```shell
./micropython/tools/mpremote/mpremote.py cp *.py :/ + cp -r www :/
```

Now press the reset button on your board to start the server!

To see log messages or soft-resetting the board you can use the MicroPython REPL interface:

```shell
./micropython/tools/mpremote/mpremote.py  # connect to REPL

# press Ctrl+C to abort the server
# press Ctrl+D to soft-reset the system
# press Ctrl+X to exit the mpremote tool
```

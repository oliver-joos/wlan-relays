// This configuration is included by all boards of this project.

// Disable SDCard to reduce firmware size by 21.5k.
#define MICROPY_HW_ENABLE_SDCARD            (0)

// Disable Ethernet LAN to reduce firmware size by 71k.
#define MICROPY_PY_NETWORK_LAN              (0)

// Disable Bluetooth to reduce firmware size by 240k!
#define MICROPY_PY_BLUETOOTH                (0)
#define MICROPY_BLUETOOTH_NIMBLE            (0)

// Disable ESPNow to reduce firmware size by 12.5k.
#define MICROPY_PY_ESPNOW                   (0)

set(IDF_TARGET esp32c3)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/ESP32_GENERIC_C3/sdkconfig.c3usb
    ${MICROPY_BOARD_DIR}/../sdkconfig.ota
)

// This configuration is for a ESP32C3 SuperMini board with 4MiB flash and Over-The-Air updates.

#include "../mpconfigboards.h"

#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "ESP32C3 SuperMini"
#endif
#ifndef MICROPY_HW_MCU_NAME
#define MICROPY_HW_MCU_NAME "ESP32C3"
#endif

// Disable UART REPL and use native USB CDC.
#define MICROPY_HW_ENABLE_UART_REPL         (0)

// Disable I2S not supported by ESP32C3.
#define MICROPY_PY_MACHINE_I2S              (0)

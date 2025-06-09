# --------------------------------------------------------------------------------------------------
#  @file  ./webapp.py
#
#  @brief  Webservices to control output pins of an ESP32 board.
#
#  @author  oliver.joos@hispeed.ch
# --------------------------------------------------------------------------------------------------
#

import json
from relay_webserver import route, get_pin, get_pwm


@route("/api/pins", methods="POST")
async def post_pins(headers, body):
    try:
        props = json.loads(body)
        for pin_name, new_value in props.items():
            pin = get_pin(pin_name)
            print(f"Set {pin_name} to {'high' if new_value else 'low'}")
            pin.value(bool(new_value))
        status = 200
    except ValueError:
        status = 400
    return status


@route("/api/pwms", methods="POST")
async def post_pwms(headers, body):
    try:
        props = json.loads(body)
        for pin_name, new_value in props.items():
            pwm = get_pwm(pin_name)
            print(f"Set {pin_name} to {new_value}")
            pwm.duty(int(new_value))
        status = 200
    except ValueError:
        status = 400
    return status

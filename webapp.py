# --------------------------------------------------------------------------------------------------
#  @file  ./webapp.py
#
#  @brief  Webservices to control output pins of an ESP32 board.
#
#  @author  oliver.joos@hispeed.ch
# --------------------------------------------------------------------------------------------------
#

import json
from relay_webserver import route, get_pin


@route("/api/pins", methods="POST")
async def post_pins(headers, body):
    try:
        props = json.loads(body)
        for pin_name, new_value in props.items():
            pin = get_pin(pin_name)
            print(f"Set {pin} to {'high' if new_value else 'low'}")
            pin.value(bool(new_value))
        status = 200
    except ValueError:
        status = 400
    return status

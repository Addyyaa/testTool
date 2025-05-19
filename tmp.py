from datetime import datetime, timedelta
import logging

config = {
    "on_time": "00:00",
    "off_time": "23:50",
}


def set_timer_screen_on_off():
    on_time = config["on_time"]
    off_time = config["off_time"]
    on_hour = datetime.strptime(on_time, "%H:%M").hour
    on_min = datetime.strptime(on_time, "%H:%M").minute
    off_hour = datetime.strptime(off_time, "%H:%M").hour
    off_min = datetime.strptime(off_time, "%H:%M").minute
    on = on_hour << 8 | on_min
    off = off_hour << 8 | off_min
    if on is not None and off is not None:
        print(f"on:{on}, off:{off}")

    else:
        # This 'else' might be unreachable if strptime fails first
        logging.error(
            f"计算出的 on/off 值无效 (on={on}, off={off}) 或时间格式错误 (on_time={on_time}, off_time={off_time})")
        # Consider not exiting the whole script here, maybe return False
        # sys.exit()
        return False  # Return False instead of exiting


set_timer_screen_on_off()

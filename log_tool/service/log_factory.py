class LogTypeStrategy:
    def __init__(self, name, path):
        self.name = name
        self.path = path

    def get_pack_cmd(self):
        if self.name == "daemon":
            return f"tar czf {self.name}.tar.gz {self.path}"
        else:
            return f"tar czf {self.name}.tar.gz {self.path}/"

class LogFactory:
    _log_types = {
        "视频": LogTypeStrategy("video", "video"),
        "图片": LogTypeStrategy("pintura", "pintura"),
        "mqtt": LogTypeStrategy("mqtt", "mqtt"),
        "daemon": LogTypeStrategy("daemon", "daemon.log"),
        "screen": LogTypeStrategy("screen", "screen"),
        "蓝牙": LogTypeStrategy("ble", "ble"),
        "misc": LogTypeStrategy("misc", "misc"),
    }

    @classmethod
    def get_log_strategy(cls, name):
        return cls._log_types[name]

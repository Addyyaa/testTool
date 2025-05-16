import json, os

class HistoryService:
    _instance = None
    _file = "ip_history.json"

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        if os.path.exists(self._file):
            with open(self._file, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = []

    def add(self, ip):
        if ip not in self.history:
            self.history.insert(0, ip)
            self._save()

    def clear(self):
        self.history = []
        self._save()

    def _save(self):
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False)

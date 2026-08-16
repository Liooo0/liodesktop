"""Service Manager: 服务注册/状态机(online/offline/starting/error/unknown)"""
import time

STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"
STATUS_STARTING = "starting"
STATUS_ERROR = "error"
STATUS_UNKNOWN = "unknown"

class Service:
    def __init__(self, name, check=None, start=None, stop=None):
        self.name = name
        self.check = check      # callable -> bool(可达)
        self.start = start      # callable(可选)
        self.stop = stop        # callable(可选)
        self.status = STATUS_UNKNOWN
        self.last_error = ""
        self.last_check = 0.0

class ServiceManager:
    def __init__(self):
        self.services = {}

    def register(self, name, check=None, start=None, stop=None):
        self.services[name] = Service(name, check, start, stop)

    def probe(self, name):
        """探测单个服务,更新状态"""
        svc = self.services.get(name)
        if not svc:
            return None
        try:
            if svc.check and svc.check():
                svc.status = STATUS_ONLINE
                svc.last_error = ""
            else:
                svc.status = STATUS_OFFLINE
        except Exception as e:
            svc.status = STATUS_ERROR
            svc.last_error = str(e)[:200]
        svc.last_check = time.time()
        return svc.status

    def probe_all(self):
        return {name: self.probe(name) for name in self.services}

    def status_map(self):
        return {name: {"status": svc.status, "error": svc.last_error}
                for name, svc in self.services.items()}

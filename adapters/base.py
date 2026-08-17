"""Adapter 接口(冻结): 所有能力适配器必须实现 health() 和 describe()"""
from abc import ABC, abstractmethod


class Adapter(ABC):
    name = "base"

    @abstractmethod
    def health(self) -> bool:
        """服务可达性探测"""

    def describe(self) -> dict:
        return {"name": self.name, "kind": type(self).__name__}

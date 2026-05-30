from abc import ABC, abstractmethod


class BaseRing(ABC):
    def __init__(self, address: str):
        self.address = address

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def get_battery(self):
        pass

    @abstractmethod
    async def sync_steps(self):
        pass
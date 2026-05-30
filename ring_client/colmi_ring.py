from datetime import datetime, timezone

from colmi_r02_client.client import Client
from colmi_r02_client.steps import NoData

from ring_client.base_ring import BaseRing


class ColmiRing(BaseRing):
    def __init__(self, address: str):
        super().__init__(address)
        self.client = Client(address)

    async def connect(self):
        await self.client.connect()

    async def disconnect(self):
        await self.client.disconnect()

    async def get_battery(self):
        return await self.client.get_battery()

    async def sync_steps(self, target_date=None):
        if target_date is None:
            target_date = datetime.now(timezone.utc)

        details = await self.client.get_steps(target_date)

        if isinstance(details, NoData):
            return []

        return details
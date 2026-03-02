# https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items/{asin}

from backend.clients.spapi.base import SPAPIClient


class CatalogClient():

    def __init__(self, spapi_client: SPAPIClient):
        self.client = spapi_client

    async def get_catalog_item(self, asin: str, marketplace_id: list[str]) -> dict:
        endpoint = f"catalog/2022-04-01/items/{asin}"

        return await self.client.get(
            endpoint,
            params={"marketplaceIds": marketplace_id}
        )

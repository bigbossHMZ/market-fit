# https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items/{asin}

class CatalogClient():
    async def get_catalog_item(self, asin: str, marketplace_id: str) -> dict:
        return {"catalog_item": {"asin": asin, "marketplace_id": marketplace_id}};

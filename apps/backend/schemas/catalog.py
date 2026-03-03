from dataclasses import dataclass


@dataclass
class CatalogItemSummary:
    marketplace_id: str
    item_name: str
    brand: str | None


@dataclass
class CatalogItem:
    asin: str
    summaries: list[CatalogItemSummary]

    @classmethod
    def from_api_response(cls, data: dict) -> "CatalogItem":
        summaries = [
            CatalogItemSummary(
                marketplace_id=s["marketplaceId"],
                item_name=s.get("itemName", ""),
                brand=s.get("brand"),
            )
            for s in data.get("summaries", [])
        ]
        return cls(asin=data["asin"], summaries=summaries)

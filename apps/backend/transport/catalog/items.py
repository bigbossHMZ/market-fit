from pydantic import Field

from backend.transport.base import SPAPITransport


# summaries
class BrowseClassificationTransport(SPAPITransport):
    display_name: str = Field(alias="displayName")
    classification_id: str = Field(alias="classificationId")


class CatalogItemSummaryTransport(SPAPITransport):
    marketplace_id: str = Field(alias="marketplaceId")
    item_name: str = Field(alias="itemName", default="")
    brand: str | None = Field(alias="brand", default=None)
    color: str | None = Field(alias="color", default=None)
    item_classification: str | None = Field(alias="itemClassification", default=None)
    manufacturer: str | None = Field(alias="manufacturer", default=None)
    model_number: str | None = Field(alias="modelNumber", default=None)
    package_quantity: int | None = Field(alias="packageQuantity", default=None)
    part_number: str | None = Field(alias="partNumber", default=None)
    size: str | None = Field(alias="size", default=None)
    style: str | None = Field(alias="style", default=None)
    browse_classification: BrowseClassificationTransport | None = Field(alias="browseClassification", default=None)
    website_display_group: str | None = Field(alias="websiteDisplayGroup", default=None)
    website_display_group_name: str | None = Field(alias="websiteDisplayGroupName", default=None)


# salesRanks
class ClassificationRankTransport(SPAPITransport):
    classification_id: str = Field(alias="classificationId")
    title: str = Field(alias="title")
    rank: int = Field(alias="rank")
    link: str | None = Field(alias="link", default=None)


class DisplayGroupRankTransport(SPAPITransport):
    website_display_group: str = Field(alias="websiteDisplayGroup")
    title: str = Field(alias="title")
    rank: int = Field(alias="rank")
    link: str | None = Field(alias="link", default=None)


class CatalogItemSalesRankTransport(SPAPITransport):
    marketplace_id: str = Field(alias="marketplaceId")
    classification_ranks: list[ClassificationRankTransport] = Field(alias="classificationRanks", default_factory=list)
    display_group_ranks: list[DisplayGroupRankTransport] = Field(alias="displayGroupRanks", default_factory=list)


# root
class CatalogItemTransport(SPAPITransport):
    asin: str = Field(alias="asin")
    summaries: list[CatalogItemSummaryTransport] | None = Field(alias="summaries", default=None)
    sales_ranks: list[CatalogItemSalesRankTransport] | None = Field(alias="salesRanks", default=None)

    # Unstructured — keys are product-type-specific attribute names from
    # Amazon's catalog schema. Hundreds of possible keys, varies by category.
    attributes: dict[str, list[dict]] | None = Field(alias="attributes", default=None)

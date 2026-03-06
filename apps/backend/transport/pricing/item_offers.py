from pydantic import Field

from backend.transport.base import SPAPITransport


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class MoneyAmountTransport(SPAPITransport):
    currency_code: str = Field(alias="CurrencyCode")
    amount: float = Field(alias="Amount")


class PointsTransport(SPAPITransport):
    points_number: int = Field(alias="PointsNumber")
    points_monetary_value: MoneyAmountTransport = Field(alias="PointsMonetaryValue")


# ---------------------------------------------------------------------------
# Identifier
# ---------------------------------------------------------------------------

class IdentifierTransport(SPAPITransport):
    marketplace_id: str = Field(alias="MarketplaceId")
    asin: str = Field(alias="ASIN")
    seller_sku: str | None = Field(alias="SellerSKU", default=None)
    item_condition: str | None = Field(alias="ItemCondition", default=None)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class OfferCountTransport(SPAPITransport):
    condition: str = Field(alias="condition")
    fulfillment_channel: str = Field(alias="fulfillmentChannel")
    offer_count: int = Field(alias="OfferCount")


class LowestPriceTransport(SPAPITransport):
    condition: str = Field(alias="condition")
    fulfillment_channel: str = Field(alias="fulfillmentChannel")
    offer_type: str = Field(alias="offerType")
    quantity_tier: int | None = Field(alias="quantityTier", default=None)
    quantity_discount_type: str | None = Field(alias="quantityDiscountType", default=None)
    landed_price: MoneyAmountTransport | None = Field(alias="LandedPrice", default=None)
    listing_price: MoneyAmountTransport = Field(alias="ListingPrice")
    shipping: MoneyAmountTransport | None = Field(alias="Shipping", default=None)
    points: PointsTransport | None = Field(alias="Points", default=None)


class BuyBoxPriceTransport(SPAPITransport):
    condition: str = Field(alias="condition")
    offer_type: str = Field(alias="offerType")
    quantity_tier: int | None = Field(alias="quantityTier", default=None)
    quantity_discount_type: str | None = Field(alias="quantityDiscountType", default=None)
    landed_price: MoneyAmountTransport | None = Field(alias="LandedPrice", default=None)
    listing_price: MoneyAmountTransport = Field(alias="ListingPrice")
    shipping: MoneyAmountTransport | None = Field(alias="Shipping", default=None)
    points: PointsTransport | None = Field(alias="Points", default=None)
    seller_id: str | None = Field(alias="sellerId", default=None)


class SalesRankingTransport(SPAPITransport):
    product_category_id: str = Field(alias="ProductCategoryId")
    rank: int = Field(alias="Rank")


class SummaryTransport(SPAPITransport):
    total_offer_count: int = Field(alias="TotalOfferCount")
    number_of_offers: list[OfferCountTransport] = Field(alias="NumberOfOffers", default_factory=list)
    lowest_prices: list[LowestPriceTransport] = Field(alias="LowestPrices", default_factory=list)
    buy_box_prices: list[BuyBoxPriceTransport] = Field(alias="BuyBoxPrices", default_factory=list)
    list_price: MoneyAmountTransport | None = Field(alias="ListPrice", default=None)
    competitive_price_threshold: MoneyAmountTransport | None = Field(alias="CompetitivePriceThreshold", default=None)
    suggested_lower_price_plus_shipping: MoneyAmountTransport | None = Field(alias="SuggestedLowerPricePlusShipping", default=None)
    sales_rankings: list[SalesRankingTransport] = Field(alias="SalesRankings", default_factory=list)
    buy_box_eligible_offers: list[OfferCountTransport] = Field(alias="BuyBoxEligibleOffers", default_factory=list)
    offers_available_time: str | None = Field(alias="OffersAvailableTime", default=None)


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------

class SellerFeedbackRatingTransport(SPAPITransport):
    seller_positive_feedback_rating: float | None = Field(alias="SellerPositiveFeedbackRating", default=None)
    feedback_count: int = Field(alias="FeedbackCount")


class ShippingTimeTransport(SPAPITransport):
    minimum_hours: int | None = Field(alias="minimumHours", default=None)
    maximum_hours: int | None = Field(alias="maximumHours", default=None)
    available_date: str | None = Field(alias="availableDate", default=None)
    availability_type: str | None = Field(alias="availabilityType", default=None)


class ShipsFromTransport(SPAPITransport):
    state: str | None = Field(alias="State", default=None)
    country: str | None = Field(alias="Country", default=None)


class PrimeInformationTransport(SPAPITransport):
    is_prime: bool = Field(alias="IsPrime")
    is_national_prime: bool = Field(alias="IsNationalPrime")


class QuantityDiscountPriceTransport(SPAPITransport):
    quantity_tier: int = Field(alias="quantityTier")
    quantity_discount_type: str = Field(alias="quantityDiscountType")
    listing_price: MoneyAmountTransport = Field(alias="listingPrice")


class OfferTransport(SPAPITransport):
    my_offer: bool = Field(alias="MyOffer", default=False)
    offer_type: str | None = Field(alias="offerType", default=None)
    sub_condition: str | None = Field(alias="SubCondition", default=None)
    seller_id: str | None = Field(alias="SellerId", default=None)
    condition_notes: str | None = Field(alias="ConditionNotes", default=None)
    seller_feedback_rating: SellerFeedbackRatingTransport | None = Field(alias="SellerFeedbackRating", default=None)
    shipping_time: ShippingTimeTransport | None = Field(alias="ShippingTime", default=None)
    listing_price: MoneyAmountTransport = Field(alias="ListingPrice")
    quantity_discount_prices: list[QuantityDiscountPriceTransport] = Field(alias="quantityDiscountPrices", default_factory=list)
    points: PointsTransport | None = Field(alias="Points", default=None)
    shipping: MoneyAmountTransport | None = Field(alias="Shipping", default=None)
    ships_from: ShipsFromTransport | None = Field(alias="ShipsFrom", default=None)
    is_fulfilled_by_amazon: bool = Field(alias="IsFulfilledByAmazon")
    prime_information: PrimeInformationTransport | None = Field(alias="PrimeInformation", default=None)
    is_buy_box_winner: bool = Field(alias="IsBuyBoxWinner", default=False)
    is_featured_merchant: bool = Field(alias="IsFeaturedMerchant", default=False)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorTransport(SPAPITransport):
    code: str = Field(alias="code")
    message: str = Field(alias="message")
    details: str | None = Field(alias="details", default=None)


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

class ItemOffersPayloadTransport(SPAPITransport):
    marketplace_id: str = Field(alias="marketplaceId")
    asin: str = Field(alias="ASIN")
    sku: str | None = Field(alias="SKU", default=None)
    item_condition: str | None = Field(alias="ItemCondition", default=None)
    status: str | None = Field(alias="status", default=None)
    identifier: IdentifierTransport | None = Field(alias="Identifier", default=None)
    summary: SummaryTransport | None = Field(alias="Summary", default=None)
    offers: list[OfferTransport] = Field(alias="Offers", default_factory=list)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class ItemOffersTransport(SPAPITransport):
    payload: ItemOffersPayloadTransport | None = Field(alias="payload", default=None)
    errors: list[ErrorTransport] = Field(alias="errors", default_factory=list)

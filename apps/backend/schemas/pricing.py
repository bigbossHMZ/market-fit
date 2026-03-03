from dataclasses import dataclass


@dataclass
class PricingOffer:
    listing_price: float
    currency_code: str
    is_fba: bool
    is_buy_box_winner: bool
    seller_feedback_count: int | None
    seller_positive_feedback_rating: float | None


@dataclass
class PricingResult:
    asin: str
    marketplace_id: str
    offers: list[PricingOffer]

    @classmethod
    def from_api_response(cls, data: dict, marketplace_id: str) -> "PricingResult":
        payload = data.get("payload", {})
        offers = [
            PricingOffer(
                listing_price=o["ListingPrice"]["Amount"],
                currency_code=o["ListingPrice"]["CurrencyCode"],
                is_fba=o.get("IsFulfilledByAmazon", False),
                is_buy_box_winner=o.get("IsBuyBoxWinner", False),
                seller_feedback_count=o.get("SellerFeedbackRating", {}).get("FeedbackCount"),
                seller_positive_feedback_rating=o.get("SellerFeedbackRating", {}).get("SellerPositiveFeedbackRating"),
            )
            for o in payload.get("Offers", [])
        ]
        return cls(asin=payload.get("ASIN", ""), marketplace_id=marketplace_id, offers=offers)

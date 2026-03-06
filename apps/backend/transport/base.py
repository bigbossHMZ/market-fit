from pydantic import BaseModel, ConfigDict


class SPAPITransport(BaseModel):
    """
    Base class for all SP-API transport models.

    Configures two behaviours shared by every transport object:
    - extra="ignore": unknown fields from the API are silently dropped,
        so new fields added by Amazon never break existing code.
    - populate_by_name=True: instances can be constructed using Python
        field names (snake_case) instead of aliases, which simplifies tests.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

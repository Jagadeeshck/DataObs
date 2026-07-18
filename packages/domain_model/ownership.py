from .base import ProductEntity


class Ownership(ProductEntity):
    asset_id: str
    owner: str
    owner_email: str | None = None
    stewardship_tier: str = "standard"

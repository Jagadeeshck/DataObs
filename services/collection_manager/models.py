from pydantic import BaseModel, ConfigDict


class CollectionManagerModel(BaseModel):
    model_config = ConfigDict(extra="allow")

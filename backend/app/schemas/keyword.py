from pydantic import BaseModel, Field


class KeywordOut(BaseModel):
    id: str
    keyword: str
    category: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    source_supported: bool = True

    model_config = {"from_attributes": True}


class KeywordIn(BaseModel):
    keyword: str
    category: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)


class KeywordUpdate(BaseModel):
    keyword: str | None = None
    category: str | None = None
    description: str | None = None
    aliases: list[str] | None = None

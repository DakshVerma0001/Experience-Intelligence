from pydantic import BaseModel


class SearchFilters(BaseModel):
    country: str | None = None
    state_ut: str | None = None
    client_type: str | None = None
    project_status: str | None = None
    min_contract_value_crore: float | None = None
    max_contract_value_crore: float | None = None
    keywords: list[str] | None = None
    domain: str | None = None


class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # keyword | fulltext | semantic | hybrid
    filters: SearchFilters | None = None
    limit: int = 20


class SearchResultItem(BaseModel):
    project_id: str
    project_name: str | None
    client_name: str | None
    country: str | None
    state_ut: str | None
    ai_search_summary: str | None
    score: float
    matched_keywords: list[str] = []
    match_reasons: list[str] = []


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResultItem]

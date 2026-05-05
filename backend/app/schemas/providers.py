from pydantic import BaseModel


class OAuthStartResponse(BaseModel):
    url: str


class XArchiveSummary(BaseModel):
    posts_processed: int
    sentiment_label: str
    toxicity_ratio: float


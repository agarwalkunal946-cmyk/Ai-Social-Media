from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ai Social Media"
    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    demo_mode: bool = True
    first_admin_email: str = "admin@gmail.com"
    admin_emails: str = "admin@gmail.com"
    auth_fallback_enabled: bool = True

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "ai_social_media"
    redis_url: str = "redis://localhost:6379/0"
    preview_cache_ttl_seconds: int = 300
    dashboard_cache_ttl_seconds: int = 180

    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_app_id: str = ""
    firebase_measurement_id: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/providers/youtube/callback"

    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:8000/api/providers/instagram/callback"
    meta_api_version: str = "v25.0"

    x_live_source_token: str = Field(default="", validation_alias=AliasChoices("X_LIVE_SOURCE_TOKEN", "X_APIFY_TOKEN"))
    x_live_source_actor_id: str = Field(
        default="danek~twitter-scraper-ppr",
        validation_alias=AliasChoices("X_LIVE_SOURCE_ACTOR_ID", "X_APIFY_ACTOR_ID"),
    )
    x_live_timeline_max_posts: int = Field(
        default=36,
        validation_alias=AliasChoices("X_LIVE_TIMELINE_MAX_POSTS", "X_APIFY_TIMELINE_MAX_POSTS"),
    )
    x_live_search_max_posts: int = Field(
        default=48,
        validation_alias=AliasChoices("X_LIVE_SEARCH_MAX_POSTS", "X_APIFY_SEARCH_MAX_POSTS"),
    )
    x_live_post_detail_max_posts: int = Field(
        default=1,
        validation_alias=AliasChoices("X_LIVE_POST_DETAIL_MAX_POSTS", "X_APIFY_POST_DETAIL_MAX_POSTS"),
    )
    x_live_trending_country: str = Field(
        default="United States",
        validation_alias=AliasChoices("X_LIVE_TRENDING_COUNTRY", "X_APIFY_TRENDING_COUNTRY"),
    )
    x_live_timeout_seconds: int = Field(
        default=45,
        validation_alias=AliasChoices("X_LIVE_TIMEOUT_SECONDS", "X_APIFY_TIMEOUT_SECONDS"),
    )

    uploads_dir: Path = BASE_DIR / "uploads"
    reports_dir: Path = BASE_DIR / "app" / "static" / "reports"

    sentiment_model_name: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    toxicity_model_name: str = "unitary/multilingual-toxic-xlm-roberta"
    language_model_name: str = "papluca/xlm-roberta-base-language-detection"
    embeddings_model_name: str = "intfloat/multilingual-e5-base"
    forecasting_model_name: str = "Prophet"
    emotion_model_name: str = "joeddav/distilbert-base-uncased-go-emotions-student"

    youtube_scopes: str = (
        "https://www.googleapis.com/auth/userinfo.email "
        "https://www.googleapis.com/auth/userinfo.profile "
        "https://www.googleapis.com/auth/youtube.readonly "
        "https://www.googleapis.com/auth/yt-analytics.readonly"
    )
    instagram_scopes: str = (
        "pages_show_list,pages_read_engagement,instagram_basic,"
        "instagram_manage_insights,instagram_manage_comments,business_management"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [email.strip().lower() for email in self.admin_emails.split(",") if email.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

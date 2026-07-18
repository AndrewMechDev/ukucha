from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Ukucha API"
    debug: bool = True
    database_url: str = "sqlite:///./ukucha.db"


settings = Settings()

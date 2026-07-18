from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Ukucha API"
    debug: bool = True
    database_url: str = "sqlite:///./ukucha.db"

    class Config:
        env_file = ".env"


settings = Settings()

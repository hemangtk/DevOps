"""Configuration, read from the environment (12-factor).
Name: Hemang | Enrollment number: 24bcs10209
"""
import os


class Settings:
    APP_NAME: str = "Stacks"
    APP_VERSION: str = os.getenv("APP_VERSION", "dev")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # how many days a loan runs for, configurable without a rebuild
    LOAN_DAYS: int = int(os.getenv("LOAN_DAYS", "14"))

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "stacks")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "stacks")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "stacks")

    @property
    def database_url(self) -> str:
        """An explicit DATABASE_URL wins; otherwise build one from the parts.
        Tests set DATABASE_URL to a SQLite file so they never touch Postgres."""
        explicit = os.getenv("DATABASE_URL")
        if explicit:
            return explicit
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

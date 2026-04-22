from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Definimos las variables y su tipo
    db_connection_url: str = Field(
        default="",
        validation_alias=AliasChoices("DB_CONNECTION_URL", "DATABASE_URL"),
    )
    auth_secret_key: str = "inv-bill-core-dev-secret"
    auth_token_expire_minutes: int = 480
    company_name: str = "HillyStore"
    company_tax_id: str = "0000000000000"
    company_iibb: str = "0000000000"
    company_address: str = "Calle 0001, El Llano, Bani"
    company_city: str = "Bani"
    company_start_date: str = "01/01/2024"
    company_tax_condition: str = "Responsable Inscripto"
    company_phone: str = "809-778-3748"
    invoice_tax_rate: float = 0.18
    frontend_url: str = ""
    cors_origins: str = ""
 
    model_config = SettingsConfigDict(env_file=".env", extra="ignore") 

    def model_post_init(self, __context) -> None:
        if self.db_connection_url.startswith("postgresql://"):
            self.db_connection_url = self.db_connection_url.replace(
                "postgresql://",
                "postgresql+psycopg2://",
                1,
            )

    def get_cors_origins(self) -> list[str]:
        origins: list[str] = []
        for raw_value in (self.frontend_url, self.cors_origins):
            if not raw_value:
                continue
            for origin in raw_value.split(","):
                cleaned = origin.strip().rstrip("/")
                if cleaned and cleaned not in origins:
                    origins.append(cleaned)
        return origins


# Instanciamos para usar en el proyecto
settings = Settings()

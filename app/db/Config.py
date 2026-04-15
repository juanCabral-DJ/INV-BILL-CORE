from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Definimos las variables y su tipo

    db_connection_url: str = ""

    # Configuración para leer el archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instanciamos para usar en el proyecto
settings = Settings()
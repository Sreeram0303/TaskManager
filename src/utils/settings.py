from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")
    DB_CONNECTION : str
    
    JWT_SECRET_KEY : str
    JWT_ALGORITHM : str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES :int = 30
    JWT_REFRESH_EXPIRE_DAYS : int = 7 
    
    
settings = Settings()


 

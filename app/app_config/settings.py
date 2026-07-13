import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "agent", ".env")

class Settings(BaseSettings):
    dashscope_api_key: str
    redis_url: str
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_api_key: str | None = None
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root123"
    mysql_database: str = "cloud_platform"
    jwt_secret_key: str | None = None
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    agent_demo_mode: bool = False
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra='ignore')

settings = Settings()

import os
from dotenv import load_dotenv

load_dotenv()  # Loads .env file automatically

class Settings:
    DB_SERVER: str = os.getenv("DB_SERVER")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USERNAME: str = os.getenv("DB_USERNAME")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")

settings = Settings()

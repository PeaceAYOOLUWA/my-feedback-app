import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file for local development

ENV = os.getenv("flask_env", "development").lower()

if ENV == "production":
    DB_PATH = os.getenv("DATABASE_PATH", "feedback.db")
    CSV_PATH = os.getenv("CSV_PATH", "feedback.csv")
else:
    DB_PATH = os.getenv("DATABASE_LOCAL_PATH", "feedback_local.db")
    CSV_PATH = os.getenv("CSV_LOCAL_PATH", "feedback_local.csv")

import os

class Settings:
    app_name = "IMAGE LMS API"
    environment = os.getenv("ENVIRONMENT", "development")
    jwt_secret = os.getenv("JWT_SECRET", "local-development-secret-change-before-deploy")
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://image:image@localhost:5432/image_lms")

settings = Settings()

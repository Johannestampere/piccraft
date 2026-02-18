from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    storage_dir: str = "./storage"

    stage0_grid_size: int = 64
    stage1_voxel_size: int = 64
    stage2_voxel_size: int = 64

    tripo_api_key: str = ""

    max_image_size_mb: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
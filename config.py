import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: list[int] = field(default_factory=list)
    low_stock_threshold: int = 5
    database_url: str = "sqlite+aiosqlite:///dassi_shop.db"

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "")
        if raw:
            self.admin_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        self.low_stock_threshold = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))
        self.database_url = os.getenv("DATABASE_URL", self.database_url)


settings = Settings()

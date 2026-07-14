import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
EXPORTS_DIR = PROJECT_ROOT / "exports"
DEFAULT_DB_FILE = DATA_DIR / "dassi_shop.db"


def _resolve_database_url(raw_url: str) -> str:
    prefix = "sqlite+aiosqlite:///"
    if not raw_url.startswith(prefix):
        return raw_url

    db_path = Path(raw_url[len(prefix):])
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        for legacy in (PROJECT_ROOT / "dassi_shop.db", Path.cwd() / "dassi_shop.db"):
            if legacy.exists() and legacy.resolve() != db_path.resolve():
                shutil.copy2(legacy, db_path)
                break

    db_path.parent.mkdir(parents=True, exist_ok=True)
    resolved = db_path.resolve().as_posix()
    return f"{prefix}{resolved}"


@dataclass
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: list[int] = field(default_factory=list)
    low_stock_threshold: int = 5
    database_url: str = field(
        default_factory=lambda: f"sqlite+aiosqlite:///{DEFAULT_DB_FILE.as_posix()}"
    )
    db_path: str = ""

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "")
        if raw:
            self.admin_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        self.low_stock_threshold = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))
        env_db = os.getenv("DATABASE_URL")
        if env_db:
            self.database_url = _resolve_database_url(env_db)
        else:
            self.database_url = _resolve_database_url(self.database_url)
        prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(prefix):
            self.db_path = self.database_url[len(prefix):]


settings = Settings()

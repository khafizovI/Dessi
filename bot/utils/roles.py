from config import settings
from database.models import Admin


def is_main_admin(telegram_id: int, admin: Admin | None = None) -> bool:
    if telegram_id in settings.admin_ids:
        return True
    if admin and admin.is_main:
        return True
    return False

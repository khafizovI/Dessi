from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.utils.roles import get_user_role


class MainAdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject, *args: Any) -> bool:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        if not user:
            return False
        return await get_user_role(user.id)

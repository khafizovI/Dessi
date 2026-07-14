from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.utils.roles import is_main_admin
from database.repository import AdminRepository
from database.session import async_session

MAIN_ONLY_MESSAGES = {
    "➕ Mahsulot qo'shish",
    "📊 Hisobot",
    "📜 Tarix",
    "📝 Xarajat",
    "➕ Xarajat qo'shish",
    "📋 Xarajatlar",
    "👤 Adminlar",
    "📅 Bugun",
    "📅 Kecha",
    "📆 Haftalik",
    "🗓 Oylik",
    "📆 Sana oralig'i",
    "📄 Excel",
    "📄 PDF",
    "📜 So'nggi sotuvlar",
    "↩️ Sotuvni bekor qilish",
    "👥 Adminlar ro'yxati",
    "➕ Admin qo'shish",
    "🗑 Admin o'chirish",
    "🗑 Mahsulot o'chirish",
}

MAIN_ONLY_CALLBACKS = ("adm_del:", "cancel_sale:", "prod_del:")


class AdminMiddleware(BaseMiddleware):
    def _command(self, event: TelegramObject) -> str | None:
        if isinstance(event, Message) and event.text:
            return event.text.split()[0].split("@")[0].lower()
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return None

        cmd = self._command(event)

        async with async_session() as session:
            repo = AdminRepository(session)
            admin = await repo.get_by_telegram_id(user.id)

        if not admin:
            if cmd == "/id":
                return await handler(event, data)
            return None

        main = is_main_admin(user.id, admin)
        data["is_main"] = main
        data["admin"] = admin

        if not main:
            if isinstance(event, Message) and event.text in MAIN_ONLY_MESSAGES:
                await event.answer(
                    "🔒 Bu bo'lim faqat bosh adminlar uchun!\n"
                    "💰 Siz faqat Sotuv va Ombordan foydalanasiz."
                )
                return None
            if isinstance(event, CallbackQuery) and event.data:
                if any(event.data.startswith(p) for p in MAIN_ONLY_CALLBACKS):
                    await event.answer("🔒 Ruxsat yo'q!", show_alert=True)
                    return None

        return await handler(event, data)

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import ADMIN_KB, CANCEL_KB, admin_delete_kb, get_menu
from bot.states.forms import AddAdminStates
from bot.utils.roles import is_main_admin
from config import settings
from database.repository import AdminRepository
from database.session import async_session

router = Router()


@router.message(F.text == "👤 Adminlar")
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👤 <b>Adminlar boshqaruvi</b>\n\n"
        "👇 Quyidagilardan birini tanlang:",
        reply_markup=ADMIN_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "👥 Adminlar ro'yxati")
async def list_admins(message: Message):
    async with async_session() as session:
        repo = AdminRepository(session)
        admins = await repo.get_all()

    if not admins:
        await message.answer(
            "📭 Hozircha adminlar yo'q.\n"
            "➕ Yangi admin qo'shing!",
            reply_markup=ADMIN_KB,
        )
        return

    lines = ["👥 <b>Adminlar ro'yxati:</b>\n"]
    for i, admin in enumerate(admins, 1):
        role = "👑 Bosh admin" if is_main_admin(admin.telegram_id, admin) else "💼 Sotuvchi"
        lines.append(f"  {i}. {role} — <b>{admin.name}</b>")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=ADMIN_KB)


@router.message(F.text == "➕ Admin qo'shish")
async def add_admin_start(message: Message, state: FSMContext):
    await state.set_state(AddAdminStates.name)
    await message.answer(
        "➕ <b>Yangi admin qo'shish</b>\n\n"
        "👤 Admin ismini kiriting:\n"
        "<i>Masalan: Ali, Doston, Malika...</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddAdminStates.name)
async def add_admin_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Ism juda qisqa! 👤 Kamida 2 ta harf kiriting.")
        return

    await state.update_data(name=name)
    await state.set_state(AddAdminStates.telegram_id)
    await message.answer(
        f"👤 <b>Ism:</b> {name}\n\n"
        f"🆔 Endi <b>{name}</b> botga /id buyrug'ini yuborsin.\n"
        f"Chiqgan ID ni shu yerga kiriting:",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddAdminStates.telegram_id)
async def add_admin_telegram_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ Noto'g'ri ID! 🆔 Faqat raqam kiriting.\n"
            "<i>Masalan: 123456789</i>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    async with async_session() as session:
        repo = AdminRepository(session)
        existing = await repo.get_by_telegram_id(telegram_id)
        if existing:
            await message.answer(
                f"⚠️ Bu ID allaqachon ro'yxatda!\n"
                f"👤 <b>{existing.name}</b>",
                reply_markup=ADMIN_KB,
                parse_mode="HTML",
            )
            await state.clear()
            return

        admin = await repo.create(
            telegram_id=telegram_id, name=data["name"], is_main=False
        )

    await state.clear()
    await message.answer(
        f"✅ <b>Admin muvaffaqiyatli qo'shildi!</b>\n\n"
        f"👤 <b>Ism:</b> {admin.name}\n"
        f"🆔 <b>ID:</b> {admin.telegram_id}\n"
        f"💼 <b>Rol:</b> Sotuvchi (faqat Sotuv va Ombor)",
        reply_markup=get_menu(True),
        parse_mode="HTML",
    )


@router.message(F.text == "🗑 Admin o'chirish")
async def delete_admin_start(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        repo = AdminRepository(session)
        admins = await repo.get_all()

    deletable = [a for a in admins if a.telegram_id != message.from_user.id]

    if not deletable:
        await message.answer(
            "📭 O'chirish uchun boshqa admin yo'q.",
            reply_markup=ADMIN_KB,
        )
        return

    await message.answer(
        "🗑 <b>O'chirish uchun adminni tanlang:</b>",
        reply_markup=admin_delete_kb(deletable),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_del:"))
async def delete_admin_confirm(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    async with async_session() as session:
        repo = AdminRepository(session)
        admins = await repo.get_all()
        target = await repo.get_by_id(admin_id)

        if not target:
            await callback.answer("⚠️ Admin topilmadi!", show_alert=True)
            return

        if len(admins) <= 1:
            await callback.answer(
                "⚠️ Oxirgi adminni o'chirib bo'lmaydi!", show_alert=True
            )
            return

        if target.telegram_id == user_id:
            await callback.answer(
                "⚠️ O'zingizni o'chirib bo'lmaydi!", show_alert=True
            )
            return

        if target.is_main and target.telegram_id in settings.admin_ids:
            await callback.answer(
                "⚠️ Bosh adminni o'chirib bo'lmaydi!", show_alert=True
            )
            return

        name = target.name
        await repo.delete(admin_id)

    await callback.message.edit_text(
        f"✅ <b>{name}</b> adminlar ro'yxatidan o'chirildi! 🗑",
        parse_mode="HTML",
    )
    await callback.answer()

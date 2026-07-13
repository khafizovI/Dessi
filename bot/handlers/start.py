from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.menus import get_menu

router = Router()

WELCOME_MAIN = (
    "👋 <b>Assalomu alaykum!</b>\n"
    "🏪 <b>Dassi</b> — Tez sotuv va foyda hisoboti\n\n"
    "👑 Siz <b>bosh admin</b> sifatida kirdingiz.\n"
    "👇 Quyidagi tugmalardan birini tanlang:"
)

WELCOME_SELLER = (
    "👋 <b>Assalomu alaykum!</b>\n"
    "🏪 <b>Dassi</b> — Sotuv boti\n\n"
    "👤 Siz <b>sotuvchi</b> sifatida kirdingiz.\n"
    "💰 Sotuv va 📦 Ombor bo'limlaridan foydalaning."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, is_main: bool):
    await state.clear()
    text = WELCOME_MAIN if is_main else WELCOME_SELLER
    await message.answer(text, reply_markup=get_menu(is_main), parse_mode="HTML")


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(str(message.from_user.id), parse_mode=None)


@router.message(lambda m: m.text == "🔙 Orqaga")
async def cmd_back(message: Message, state: FSMContext, is_main: bool):
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=get_menu(is_main))


@router.message(lambda m: m.text == "❌ Bekor qilish")
async def cmd_cancel(message: Message, state: FSMContext, is_main: bool):
    await state.clear()
    await message.answer(
        "❌ Amal bekor qilindi.\n🏠 Asosiy menyuga qaytdingiz.",
        reply_markup=get_menu(is_main),
    )

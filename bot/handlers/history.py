from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import CANCEL_KB, EXPENSE_KB, HISTORY_KB, sale_cancel_kb
from bot.states.forms import AddExpenseStates
from database.repository import AdminRepository, ExpenseRepository, SaleRepository
from database.session import async_session
from services.report_builder import format_expense_lines

router = Router()


@router.message(F.text == "📝 Xarajat")
async def expense_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 <b>Xarajatlar boshqaruvi</b>\n\n👇 Tanlang:",
        reply_markup=EXPENSE_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "➕ Xarajat qo'shish")
async def add_expense_start(message: Message, state: FSMContext):
    await state.set_state(AddExpenseStates.description)
    await message.answer(
        "➕ <b>Xarajat qo'shish</b>\n\n"
        "📋 Sabab / tavsifni kiriting:\n"
        "<i>Masalan: Reklama, Yetkazib berish...</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Xarajatlar")
async def list_expenses(message: Message):
    async with async_session() as session:
        repo = ExpenseRepository(session)
        expenses = await repo.get_all()

    if not expenses:
        await message.answer(
            "📭 Hozircha xarajatlar yo'q.\n➕ Xarajat qo'shing!",
            reply_markup=EXPENSE_KB,
        )
        return

    items = [
        {
            "description": e.description,
            "amount": e.amount,
            "admin_name": e.admin_name,
            "date": e.created_at.strftime("%d.%m.%Y %H:%M"),
        }
        for e in expenses
    ]
    total = sum(e.amount for e in expenses)
    lines = ["📋 <b>Xarajatlar ro'yxati:</b>\n"]
    lines.extend(format_expense_lines(items, total))

    text = "\n".join(lines)
    if len(text) > 4000:
        await message.answer(text[:4000], parse_mode="HTML")
        await message.answer(text[4000:], parse_mode="HTML", reply_markup=EXPENSE_KB)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=EXPENSE_KB)


@router.message(AddExpenseStates.description)
async def expense_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddExpenseStates.amount)
    await message.answer(
        "💵 <b>Summa kiriting (so'm):</b>\n"
        "<i>Masalan: 500000</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddExpenseStates.amount)
async def expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ To'g'ri summa kiriting!\n💵 Masalan: 500000")
        return

    data = await state.get_data()
    async with async_session() as session:
        admin_repo = AdminRepository(session)
        expense_repo = ExpenseRepository(session)
        admin = await admin_repo.get_by_telegram_id(message.from_user.id)
        admin_name = admin.name if admin else ""
        expense = await expense_repo.create(
            data["description"], amount, admin_name
        )

    await state.clear()
    await message.answer(
        f"✅ <b>Xarajat qo'shildi!</b>\n\n"
        f"📋 <b>{expense.description}</b>\n"
        f"💵 <b>{expense.amount:,.0f}</b> so'm",
        reply_markup=EXPENSE_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "📜 Tarix")
async def history_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📜 <b>Sotuvlar tarixi</b>\n\n👇 Tanlang:",
        reply_markup=HISTORY_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "📜 So'nggi sotuvlar")
async def show_history(message: Message):
    async with async_session() as session:
        repo = SaleRepository(session)
        sales = await repo.get_history(limit=20)

    if not sales:
        await message.answer(
            "📭 Hozircha sotuvlar yo'q.",
            reply_markup=HISTORY_KB,
        )
        return

    lines = ["📜 <b>So'nggi sotuvlar:</b>\n"]
    for s in sales:
        product_name = s.product.name if s.product else "?"
        time_str = s.created_at.strftime("%d.%m %H:%M")
        total = s.sale_price * s.quantity
        admin_label = s.admin_name or "Noma'lum"
        lines.append(
            f"🕐 {time_str}\n"
            f"👤 {admin_label}\n"
            f"👕 {product_name}\n"
            f"🔢 {s.quantity} dona — 💰 {total:,.0f} so'm\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        await message.answer(text[:4000], parse_mode="HTML")
        await message.answer(text[4000:], parse_mode="HTML", reply_markup=HISTORY_KB)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=HISTORY_KB)


@router.message(F.text == "↩️ Sotuvni bekor qilish")
async def cancel_sale_start(message: Message):
    async with async_session() as session:
        repo = SaleRepository(session)
        sales = await repo.get_recent_for_cancel(limit=15)

    if not sales:
        await message.answer(
            "📭 Bekor qilish uchun sotuv yo'q.",
            reply_markup=HISTORY_KB,
        )
        return

    await message.answer(
        "↩️ <b>Bekor qilish uchun sotuvni tanlang:</b>\n"
        "<i>Mahsulot omborga qaytadi</i>",
        reply_markup=sale_cancel_kb(sales),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cancel_sale:"))
async def cancel_sale_confirm(callback: CallbackQuery):
    sale_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        repo = SaleRepository(session)
        sale = await repo.cancel(sale_id)

    if not sale:
        await callback.answer("⚠️ Sotuv topilmadi yoki allaqachon bekor!", show_alert=True)
        return

    product_name = sale.product.name if sale.product else "?"
    await callback.message.edit_text(
        f"✅ <b>Sotuv bekor qilindi!</b>\n\n"
        f"👕 {product_name}\n"
        f"🔢 {sale.quantity} ta omborga qaytdi ↩️",
        parse_mode="HTML",
    )
    await callback.answer()

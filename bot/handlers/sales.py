from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import CANCEL_KB, PRICE_KB, get_menu, product_list_kb
from bot.states.forms import SellProductStates
from config import settings
from database.repository import AdminRepository, ProductRepository, SaleRepository
from database.session import async_session

router = Router()


async def _complete_sale(
    message: Message, state: FSMContext, sale_price: float, is_main: bool = True
):
    data = await state.get_data()
    product_id = data["product_id"]
    qty = data["quantity"]

    async with async_session() as session:
        product_repo = ProductRepository(session)
        sale_repo = SaleRepository(session)
        admin_repo = AdminRepository(session)
        product = await product_repo.get_by_id(product_id)
        admin = await admin_repo.get_by_telegram_id(message.from_user.id)

        if not product:
            await state.clear()
            await message.answer("❌ Mahsulot topilmadi!", reply_markup=get_menu(is_main))
            return

        if product.quantity < qty:
            await message.answer(
                f"⚠️ Omborda yetarli mahsulot yo'q!\n📦 Mavjud: <b>{product.quantity}</b> ta",
                parse_mode="HTML",
            )
            return

        sale = await sale_repo.create(product, qty, sale_price, admin)

    await state.clear()
    total = sale.sale_price * sale.quantity
    profit = (sale.sale_price - sale.cost_price) * sale.quantity
    admin_name = sale.admin_name or "Noma'lum"
    discount = ""
    if sale_price != data.get("default_price"):
        discount = f"\n💱 Chegirma: <b>{data['default_price']:,.0f}</b> → <b>{sale_price:,.0f}</b> so'm"

    text = (
        f"✅ <b>Sotuv qayd etildi!</b>\n\n"
        f"👤 Sotuvchi: <b>{admin_name}</b>\n"
        f"👕 <b>{data['product_name']}</b>\n"
        f"🔢 Sotildi: <b>{sale.quantity}</b> ta\n"
        f"💰 Jami: <b>{total:,.0f}</b> so'm\n"
        f"✨ Foyda: <b>{profit:,.0f}</b> so'm"
        f"{discount}\n"
        f"📦 Qoldiq: <b>{product.quantity}</b> ta"
    )
    await message.answer(text, reply_markup=get_menu(is_main), parse_mode="HTML")

    if product.quantity <= settings.low_stock_threshold:
        await message.answer(
            f"⚠️ <b>{product.name}</b> {product.quantity} dona qoldi!",
            parse_mode="HTML",
        )


@router.message(F.text.in_({"💰 Sotuv qayd etish", "💰 Sotuv"}))
async def sell_start(message: Message, state: FSMContext, is_main: bool = True):
    async with async_session() as session:
        repo = ProductRepository(session)
        products = await repo.get_all()

    available = [p for p in products if p.quantity > 0]
    if not available:
        await message.answer(
            "📭 Sotish uchun mahsulot yo'q!\n➕ Avval mahsulot qo'shing.",
            reply_markup=get_menu(is_main),
        )
        return

    await state.set_state(SellProductStates.select_product)
    await message.answer(
        "💰 <b>Sotuv qayd etish</b>\n\n👕 Mahsulotni tanlang:",
        reply_markup=product_list_kb(available, prefix="sell"),
        parse_mode="HTML",
    )


@router.callback_query(SellProductStates.select_product, F.data.startswith("sell:"))
async def sell_select_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        repo = ProductRepository(session)
        product = await repo.get_by_id(product_id)

    if not product or product.quantity <= 0:
        await callback.answer("⚠️ Mahsulot topilmadi yoki tugagan!", show_alert=True)
        return

    await state.update_data(
        product_id=product_id,
        product_name=product.name,
        default_price=product.sale_price,
    )
    await state.set_state(SellProductStates.quantity)
    await callback.message.answer(
        f"👕 <b>{product.name}</b> ({product.sku})\n"
        f"📦 Omborda: <b>{product.quantity}</b> ta\n"
        f"🏷 Narxi: <b>{product.sale_price:,.0f}</b> so'm\n\n"
        f"🔢 Sotilgan sonini kiriting:",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SellProductStates.quantity)
async def sell_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Musbat butun son kiriting!\n🔢 Masalan: 1")
        return

    await state.update_data(quantity=qty)
    await state.set_state(SellProductStates.custom_price)
    data = await state.get_data()
    await message.answer(
        f"🏷 Standart narx: <b>{data['default_price']:,.0f}</b> so'm\n\n"
        f"Boshqa narxda sotildimi?",
        reply_markup=PRICE_KB,
        parse_mode="HTML",
    )


@router.message(SellProductStates.custom_price, F.text == "✅ Standart narx")
async def sell_standard_price(message: Message, state: FSMContext, is_main: bool = True):
    data = await state.get_data()
    await _complete_sale(message, state, data["default_price"], is_main)


@router.message(SellProductStates.custom_price, F.text == "💱 Boshqa narx")
async def sell_ask_custom_price(message: Message, state: FSMContext):
    await message.answer(
        "💱 <b>Sotilgan narxni kiriting (1 dona, so'm):</b>\n"
        "<i>Masalan: 300000</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(SellProductStates.custom_price)
async def sell_custom_price(message: Message, state: FSMContext, is_main: bool = True):
    if message.text in ("✅ Standart narx", "💱 Boshqa narx"):
        return
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ To'g'ri narx kiriting!\n💱 Masalan: 300000")
        return
    await _complete_sale(message, state, price, is_main)

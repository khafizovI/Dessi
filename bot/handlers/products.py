from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import (
    CANCEL_KB,
    SKIP_IMAGE_KB,
    get_inventory_kb,
    get_menu,
    product_delete_kb,
)
from bot.states.forms import AddProductStates
from config import settings
from database.repository import ProductRepository
from database.session import async_session

router = Router()


@router.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(message: Message, state: FSMContext):
    await state.set_state(AddProductStates.image)
    await message.answer(
        "➕ <b>Yangi mahsulot qo'shish</b>\n\n"
        "📸 Mahsulot rasmini yuboring:",
        reply_markup=SKIP_IMAGE_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.image, F.photo)
async def add_product_image(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=file_id)
    await state.set_state(AddProductStates.name)
    await message.answer(
        "👕 <b>Mahsulot nomini kiriting:</b>\n"
        "<i>Masalan: Qora Atlas ko'ylak</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.image, F.text == "⏭ Rasm yo'q")
async def add_product_skip_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=None)
    await state.set_state(AddProductStates.name)
    await message.answer(
        "👕 <b>Mahsulot nomini kiriting:</b>\n"
        "<i>Masalan: Qora Atlas ko'ylak</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.image)
async def add_product_image_invalid(message: Message):
    await message.answer(
        "⚠️ Rasm yuboring yoki ⏭ Rasm yo'q tugmasini bosing.",
        reply_markup=SKIP_IMAGE_KB,
    )


@router.message(AddProductStates.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductStates.sku)
    await message.answer(
        "🔖 <b>SKU / mahsulot kodini kiriting:</b>\n"
        "<i>Masalan: DS-001</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.sku)
async def add_product_sku(message: Message, state: FSMContext):
    sku = message.text.strip().upper()
    async with async_session() as session:
        repo = ProductRepository(session)
        if await repo.get_by_sku(sku):
            await message.answer(
                f"⚠️ <b>{sku}</b> kodi allaqachon mavjud!\n"
                "🔖 Boshqa kod kiriting:",
                parse_mode="HTML",
            )
            return
    await state.update_data(sku=sku)
    await state.set_state(AddProductStates.cost_price)
    await message.answer(
        "💵 <b>Dastmoya narxini kiriting (1 dona, so'm):</b>\n"
        "<i>Masalan: 200000</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.cost_price)
async def add_product_cost(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ To'g'ri narx kiriting!\n💵 Masalan: 200000")
        return
    await state.update_data(cost_price=price)
    await state.set_state(AddProductStates.sale_price)
    await message.answer(
        "🏷 <b>Sotuv narxini kiriting (1 dona, so'm):</b>\n"
        "<i>Masalan: 350000</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.sale_price)
async def add_product_sale_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ To'g'ri narx kiriting!\n🏷 Masalan: 350000")
        return
    await state.update_data(sale_price=price)
    await state.set_state(AddProductStates.quantity)
    await message.answer(
        "📦 <b>Mavjud sonini kiriting:</b>\n"
        "<i>Masalan: 20</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(AddProductStates.quantity)
async def add_product_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Musbat butun son kiriting!\n📦 Masalan: 20")
        return

    data = await state.get_data()
    async with async_session() as session:
        repo = ProductRepository(session)
        product = await repo.create(
            name=data["name"],
            sku=data["sku"],
            quantity=qty,
            cost_price=data["cost_price"],
            sale_price=data["sale_price"],
            image_file_id=data.get("image_file_id"),
        )

    await state.clear()
    profit = product.sale_price - product.cost_price
    text = (
        f"✅ <b>Mahsulot qo'shildi!</b>\n\n"
        f"👕 <b>{product.name}</b>\n"
        f"🔖 SKU: <b>{product.sku}</b>\n"
        f"📦 Soni: <b>{product.quantity}</b> ta\n"
        f"💵 Dastmoya: <b>{product.cost_price:,.0f}</b> so'm\n"
        f"🏷 Sotuv: <b>{product.sale_price:,.0f}</b> so'm\n"
        f"✨ 1 dona foyda: <b>{profit:,.0f}</b> so'm"
    )

    if product.image_file_id:
        await message.answer_photo(
            product.image_file_id, caption=text, reply_markup=get_menu(True), parse_mode="HTML"
        )
    else:
        await message.answer(text, reply_markup=get_menu(True), parse_mode="HTML")


@router.message(F.text == "📦 Ombor")
async def inventory_menu(message: Message, state: FSMContext, is_main: bool = True):
    await state.clear()
    await message.answer(
        "📦 <b>Ombor boshqaruvi</b>\n\n👇 Tanlang:",
        reply_markup=get_inventory_kb(is_main),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Barcha mahsulotlar")
async def show_all_products(message: Message, is_main: bool = True):
    async with async_session() as session:
        repo = ProductRepository(session)
        products = await repo.get_all()

    if not products:
        await message.answer(
            "📭 Omborda mahsulot yo'q.\n➕ Yangi mahsulot qo'shing!",
            reply_markup=get_inventory_kb(is_main),
        )
        return

    lines = ["📦 <b>Ombordagi mahsulotlar:</b>\n"]
    total_items = 0
    total_value = 0.0

    for p in products:
        status = "⚠️" if p.quantity <= settings.low_stock_threshold else "✅"
        lines.append(
            f"{status} <b>{p.name}</b> ({p.sku})\n"
            f"   📊 {p.quantity} ta | "
            f"💵 {p.cost_price:,.0f} | "
            f"🏷 {p.sale_price:,.0f} so'm"
        )
        total_items += p.quantity
        total_value += p.quantity * p.cost_price

    lines.append(f"\n📊 <b>Jami:</b> {len(products)} tur, {total_items} dona")
    lines.append(f"💰 <b>Ombor qiymati:</b> {total_value:,.0f} so'm")

    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(lines), 15):
            chunk = lines[:1] + lines[1 + i : 1 + i + 15] if i == 0 else lines[1 + i : 1 + i + 15]
            await message.answer("\n".join(chunk), parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=get_inventory_kb(is_main))


@router.message(F.text == "⚠️ Kam qolganlar")
async def show_low_stock(message: Message, is_main: bool = True):
    async with async_session() as session:
        repo = ProductRepository(session)
        low = await repo.get_low_stock(settings.low_stock_threshold)

    if not low:
        await message.answer(
            f"✅ Barcha mahsulotlar yetarli!\n"
            f"⚠️ Ogohlantirish: ≤{settings.low_stock_threshold} ta",
            reply_markup=get_inventory_kb(is_main),
        )
        return

    lines = [
        f"⚠️ <b>Kam qolgan mahsulotlar</b> (≤{settings.low_stock_threshold} ta):\n"
    ]
    for p in low:
        emoji = "🔴" if p.quantity == 0 else "🟡"
        lines.append(f"{emoji} <b>{p.name}</b> — {p.quantity} dona qoldi.")

    await message.answer(
        "\n".join(lines), parse_mode="HTML", reply_markup=get_inventory_kb(is_main)
    )


@router.message(F.text == "🗑 Mahsulot o'chirish")
async def delete_product_start(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        repo = ProductRepository(session)
        products = await repo.get_all()

    if not products:
        await message.answer(
            "📭 O'chirish uchun mahsulot yo'q.",
            reply_markup=get_inventory_kb(True),
        )
        return

    await message.answer(
        "🗑 <b>O'chirish uchun mahsulotni tanlang:</b>\n"
        "<i>Sotuvlar tarixi saqlanadi</i>",
        reply_markup=product_delete_kb(products),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("prod_del:"))
async def delete_product_confirm(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        repo = ProductRepository(session)
        product = await repo.deactivate(product_id)

    if not product:
        await callback.answer("⚠️ Mahsulot topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ <b>{product.name}</b> ombordan o'chirildi! 🗑\n"
        f"🔖 SKU: {product.sku}",
        parse_mode="HTML",
    )
    await callback.answer()

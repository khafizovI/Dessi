from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Ombor"), KeyboardButton(text="➕ Mahsulot qo'shish")],
        [KeyboardButton(text="💰 Sotuv"), KeyboardButton(text="📊 Hisobot")],
        [KeyboardButton(text="📜 Tarix"), KeyboardButton(text="📝 Xarajat")],
        [KeyboardButton(text="👤 Adminlar")],
    ],
    resize_keyboard=True,
)

SELLER_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Ombor"), KeyboardButton(text="💰 Sotuv")],
    ],
    resize_keyboard=True,
)


def get_menu(is_main: bool) -> ReplyKeyboardMarkup:
    return MAIN_MENU if is_main else SELLER_MENU


CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True,
)

SKIP_IMAGE_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏭ Rasm yo'q")],
        [KeyboardButton(text="❌ Bekor qilish")],
    ],
    resize_keyboard=True,
)

REPORT_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Bugun"), KeyboardButton(text="📅 Kecha")],
        [KeyboardButton(text="📆 Haftalik"), KeyboardButton(text="🗓 Oylik")],
        [KeyboardButton(text="📆 Sana oralig'i")],
        [KeyboardButton(text="📄 Excel"), KeyboardButton(text="📄 PDF")],
        [KeyboardButton(text="🔙 Orqaga")],
    ],
    resize_keyboard=True,
)

ADMIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Adminlar ro'yxati"), KeyboardButton(text="➕ Admin qo'shish")],
        [KeyboardButton(text="🗑 Admin o'chirish"), KeyboardButton(text="🔙 Orqaga")],
    ],
    resize_keyboard=True,
)

INVENTORY_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Barcha mahsulotlar"), KeyboardButton(text="⚠️ Kam qolganlar")],
        [KeyboardButton(text="🔙 Orqaga")],
    ],
    resize_keyboard=True,
)

INVENTORY_MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Barcha mahsulotlar"), KeyboardButton(text="⚠️ Kam qolganlar")],
        [KeyboardButton(text="🗑 Mahsulot o'chirish")],
        [KeyboardButton(text="🔙 Orqaga")],
    ],
    resize_keyboard=True,
)


def get_inventory_kb(is_main: bool) -> ReplyKeyboardMarkup:
    return INVENTORY_MAIN_KB if is_main else INVENTORY_KB

HISTORY_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📜 So'nggi sotuvlar"), KeyboardButton(text="↩️ Sotuvni bekor qilish")],
        [KeyboardButton(text="🔙 Orqaga")],
    ],
    resize_keyboard=True,
)


def product_list_kb(products: list, prefix: str = "prod") -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        label = f"👕 {p.name} ({p.quantity} ta)"
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"{prefix}:{p.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_delete_kb(products: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"🗑 {p.name}", callback_data=f"prod_del:{p.id}")]
        for p in products
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_delete_kb(admins: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"🗑 {a.name}", callback_data=f"adm_del:{a.id}")]
        for a in admins
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sale_cancel_kb(sales: list) -> InlineKeyboardMarkup:
    buttons = []
    for s in sales:
        time_str = s.created_at.strftime("%d.%m %H:%M")
        name = s.product.name if s.product else "?"
        label = f"↩️ {time_str} | {name} | {s.quantity} ta"
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"cancel_sale:{s.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)

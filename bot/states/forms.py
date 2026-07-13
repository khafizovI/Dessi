from aiogram.fsm.state import State, StatesGroup


class AddProductStates(StatesGroup):
    image = State()
    name = State()
    sku = State()
    cost_price = State()
    sale_price = State()
    quantity = State()


class SellProductStates(StatesGroup):
    select_product = State()
    quantity = State()
    custom_price = State()


class AddExpenseStates(StatesGroup):
    description = State()
    amount = State()


class AddAdminStates(StatesGroup):
    name = State()
    telegram_id = State()


class ReportStates(StatesGroup):
    date_from = State()
    date_to = State()

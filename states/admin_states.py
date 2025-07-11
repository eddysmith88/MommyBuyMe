from aiogram.fsm.state import StatesGroup, State


class AdminCreation(StatesGroup):
    waiting_for_admin_id_and_city = State()
    waiting_for_admin_name = State()

class AdminDeletion(StatesGroup):
    waiting_for_admin_id = State()

class PromoCreation(StatesGroup):
    waiting_for_text = State()
    waiting_for_expire_date = State()


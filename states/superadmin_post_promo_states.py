from aiogram.fsm.state import StatesGroup, State


class CreatePostToCity(StatesGroup):
    waiting_for_city = State()
    waiting_for_text = State()
    waiting_for_photo = State()


class CreatePromoToCity(StatesGroup):
    waiting_for_city = State()
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_date = State()


class EditPromo(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_date = State()
    promo_id = State()


class EditPost(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    post_id = State()


class RejectPromo(StatesGroup):
    waiting_for_comment = State()
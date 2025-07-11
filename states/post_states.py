from aiogram.fsm.state import StatesGroup, State


class PostCreation(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()


class RejectPost(StatesGroup):
    waiting_for_comment = State()


class RejectPromoFSM(StatesGroup):
    waiting_for_comment = State()
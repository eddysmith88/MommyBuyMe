from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from db.models import Promo, Post
from info import cities


def send_post_kb(post: Post) -> InlineKeyboardMarkup:
    inline = [
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_post:{post.id}")],
        [InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"delete_post:{post.id}")],
        [InlineKeyboardButton(text="🚫 Відхилити", callback_data=f"send_reject_post:{post.id}:{post.author_id}")],
        [InlineKeyboardButton(text="📢 Відправити всім містам", callback_data=f"send_to_all:{post.id}")]
    ]

    for city in cities:
        inline.append([
            InlineKeyboardButton(
                text=f"Відправити місту {city}",
                callback_data=f"send_to_city:{post.id}:{city}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=inline)


def send_promo_kb(promo: Promo) -> InlineKeyboardMarkup:
    inline = [
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_promo:{promo.id}")],
        [InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"delete_promo:{promo.id}")],
        # [InlineKeyboardButton(text="🚫 Відхилити", callback_data=f"reject_promo:{promo.id}:{promo.author_id}")],
        [InlineKeyboardButton(text="🚫 Відхилити", callback_data=f"send_reject_promo:{promo.id}:{promo.author_id}")],
        [InlineKeyboardButton(text="📢 Відправити всім містам", callback_data=f"send_promo_to_all:{promo.id}")]
    ]

    for city_name in cities:
        inline.append([InlineKeyboardButton(
            text=f"Відправити місту {city_name}",
            callback_data=f"send_promo_to_city:{promo.id}:{city_name}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=inline)


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Інструкція з користування", callback_data="instruction")],
        [InlineKeyboardButton(text="📝 Створити новину", callback_data="create_post")],
        [InlineKeyboardButton(text="📝 Створити акційну пропозицію", callback_data="create_promo")],
        [InlineKeyboardButton(text="📋 Переглянути всі пости ", callback_data="list_posts")],
        [InlineKeyboardButton(text="📋 Переглянути всі акції", callback_data="list_promos")],
        [InlineKeyboardButton(text="🛠 Тех. підтримка", callback_data="support_co")]
    ])

def city_keyboard():
    buttons = [
        [InlineKeyboardButton(text=city_name, callback_data=f"select_city:{city_name}")]
        for city_name, _ in cities
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def city_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💡Про нас", callback_data="about"),
         InlineKeyboardButton(text="🆕Наші акції та новини", callback_data="news")],
        [InlineKeyboardButton(text="❔Часті питання", callback_data="faq"),
         InlineKeyboardButton(text="🗺Найближчі точки", callback_data="nearby")],
        [InlineKeyboardButton(text="🤝Стати партнером", callback_data="partner"),
         InlineKeyboardButton(text="🛠Тех. підтримка", callback_data="support")],
    ])


def super_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍Інструкція", callback_data="how_to_create")],
        [InlineKeyboardButton(text="👤 Створити адміна/франчайзі", callback_data="create_admin")],
        [InlineKeyboardButton(text="🗑️ Видалити адміна/франчайзі", callback_data="delete_admin")],
        [InlineKeyboardButton(text="📃Список адмінів", callback_data="admin_list")],
        [InlineKeyboardButton(text="📌Створити новину", callback_data="create_post_to_city")],
        [InlineKeyboardButton(text="📌Створити акцію", callback_data="create_promo_to_city")],
        [InlineKeyboardButton(text="🏢Переглянути новини", callback_data="show_posts_button")],
        [InlineKeyboardButton(text="🏢Переглянути акції", callback_data="show_promo_button")],
        [InlineKeyboardButton(text="Список наших локацій", callback_data="location_list")],
        [InlineKeyboardButton(text="🔄Оновити список клієнтів", callback_data="export_clients")],
        [InlineKeyboardButton(text="🗺Найближчі точки", callback_data="nearby")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])


def generate_post_action_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_post:{post_id}")],
        [InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"delete_post:{post_id}")]
    ])


def generate_promo_action_kb(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_promo:{promo_id}"),
         InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_promo:{promo_id}")]
    ])


# ❌ Клавіатура "Скасувати"
def cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")]]
    )


def check_post_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Переглянути пост", callback_data="check_post")]
    ])


def get_posts_pagination_kb(page, total_pages, base_callback, city=None):
    buttons = []
    if page > 1:
        cb = f"{base_callback}:{city}:{page-1}" if city else f"{base_callback}:{page-1}"
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=cb))
    if page < total_pages:
        cb = f"{base_callback}:{city}:{page+1}" if city else f"{base_callback}:{page+1}"
        buttons.append(InlineKeyboardButton(text="Далі ▶️", callback_data=cb))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


def get_pagination_kb(page, total_pages, base_callback, city=None):
    buttons = []
    if page > 1:
        cb = f"{base_callback}:{city}:{page-1}" if city else f"{base_callback}:{page-1}"
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=cb))
    if page < total_pages:
        cb = f"{base_callback}:{city}:{page+1}" if city else f"{base_callback}:{page+1}"
        buttons.append(InlineKeyboardButton(text="Далі ▶️", callback_data=cb))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
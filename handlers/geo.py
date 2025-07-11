"""
Обробник геопозицій
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from math import radians, cos, sin, sqrt, atan2
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from info import CITIES_LOCATION


router = Router()


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Земний радіус в км
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


@router.callback_query(F.data == "nearby")
async def request_location(callback: CallbackQuery):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📡 Надіслати геолокацію", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.answer("📍 Надішліть ваше місцезнаходження:", reply_markup=kb)
    await callback.answer()


@router.message(F.location)
async def handle_location(message: Message):
    user_lat = message.location.latitude
    user_lon = message.location.longitude

    nearest_city = None
    min_distance = float("inf")

    for city, places in CITIES_LOCATION.items():
        for place in places:
            dist = haversine(user_lat, user_lon, place["lat"], place["lon"])
            if dist < min_distance:
                min_distance = dist
                nearest_city = city

    if not nearest_city:
        return await message.answer("❌ Не вдалося визначити найближче місто.")


    text = f"🧸 Найближче місто: 🧸{nearest_city}🧸 (приблизно {min_distance:.1f} км)\n📍 Активні локації:\n\n"

    keyboard = []

    for location in CITIES_LOCATION[nearest_city]:
        address = location["address"]
        lat, lon = location["lat"], location["lon"]
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat:.7f},{lon:.7f}"

        text += f"🔘 {address}\n"
        keyboard.append([InlineKeyboardButton(text=address, url=maps_url)])

    print("🔍 Локація отримана:", message.location.latitude, message.location.longitude)
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == 'location_list')
async def show_locations(callback: CallbackQuery):
    await callback.message.answer('Тут буде список всіх локацій, можливо =)')
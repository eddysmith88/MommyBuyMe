from db.models import Client
from db.session import AsyncSessionLocal
from sqlalchemy import select

import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Ініціалізація Google Sheets
def init_gsheet(sheet_name: str):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    json_data = os.environ.get("GSPREAD_CREDENTIALS")  # назва змінної у Heroku
    if not json_data:
        raise ValueError("❌ Не знайдено GSPREAD_CREDENTIALS у змінних середовища")

    creds_dict = json.loads(json_data)  # розпарсити JSON-рядок у словник
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1

# Функція для експорту
async def export_clients_to_gsheet(sheet_name: str = "Turbo pizza чат бот"):
    sheet = init_gsheet(sheet_name)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client))
        clients = result.scalars().all()

    # Очистимо таблицю перед записом
    sheet.clear()

    # Запис заголовків
    sheet.append_row(["ID", "Telegram ID", "Ім’я", "Місто", "Телефон"])

    # Запис даних
    for c in clients:
        sheet.append_row([
            str(c.id),
            str(c.telegram_id),
            c.name or "",
            c.city,
            # c.username or "",
            # c.created_at.strftime("%d.%m.%Y %H:%M")
            c.phone_number
        ])

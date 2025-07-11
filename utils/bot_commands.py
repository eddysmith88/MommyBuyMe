from aiogram import Bot
from aiogram.types import BotCommand

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🔁 Запустити бота"),
        # Можна додати інші:
        # BotCommand(command="help", description="ℹ️ Допомога"),
    ]
    await bot.set_my_commands(commands)
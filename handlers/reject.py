from aiogram import Router, F
from aiogram.types import CallbackQuery

from filters.is_admin import IsAdmin
from info import SUPER_ADMIN_IDS


router = Router()

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data.startswith("send_reject_promo:"))
async def send_reject_promo(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        return await callback.message.answer("⚠️ Невірний формат даних для відхилення.")

    promo_id = int(parts[1])
    author_id = int(parts[2])

    try:
        await callback.bot.send_message(
            author_id,
            "❌ Ваша публікація *відхилена*, переробіть і надішліть знову.",
            parse_mode="Markdown"
        )
        await callback.message.answer("✅ Відхилення надіслано автору.")
    except Exception as e:
        await callback.message.answer(f"⚠️ Не вдалося надіслати повідомлення автору: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith("send_reject_post:"))
async def send_reject_post(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        return await callback.message.answer("⚠️ Невірний формат даних для відхилення.")

    post_id = int(parts[1])
    author_id = int(parts[2])

    try:
        await callback.bot.send_message(
            author_id,
            "❌ Ваш пост *відхилений*, переробіть і надішліть знову.",
            parse_mode="Markdown"
        )
        await callback.message.answer("✅ Відхилення надіслано автору.")
    except Exception as e:
        await callback.message.answer(f"⚠️ Не вдалося надіслати повідомлення автору: {e}")

    await callback.answer()

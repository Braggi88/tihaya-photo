import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# === НАСТРОЙКИ УСЛУГ (МЕНЯЙТЕ ЦЕНЫ ЗДЕСЬ) ===
SERVICES = {
    "restoration": {"name": "Реставрация фото", "price": 500},
    "animation": {"name": "Оживление фото", "price": 400},
    "souvenirs": {"name": "Сувениры", "price": 300},
    "editing": {"name": "Обработка фотографий", "price": 250},
}

# === ВАШИ ДАННЫЕ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!) ===
SBP_PHONE = os.getenv("SBP_PHONE", "+79XXXXXXXXX")      # ← будет из Railway
OWNER_NAME = os.getenv("OWNER_NAME", "Ваше Имя")        # ← будет из Railway

# === СОСТОЯНИЯ ЗАКАЗА ===
class OrderStates(StatesGroup):
    choosing_service = State()
    confirming = State()
    awaiting_payment = State()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v["name"], callback_data=f"service_{k}")]
        for k, v in SERVICES.items()
    ])
    await message.answer("Выберите услугу:", reply_markup=kb)
    await state.set_state(OrderStates.choosing_service)

@dp.callback_query(OrderStates.choosing_service, F.data.startswith("service_"))
async def choose(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split("_")[1]
    if key not in SERVICES:
        await callback.answer("❌ Ошибка")
        return
    service = SERVICES[key]
    await state.update_data(key=key, price=service["price"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{key}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    await callback.message.edit_text(
        f"Вы выбрали:\n<b>{service['name']}</b>\nСтоимость: <b>{service['price']} ₽</b>",
        reply_markup=kb, parse_mode="HTML"
    )
    await state.set_state(OrderStates.confirming)

@dp.callback_query(OrderStates.confirming, F.data.startswith("confirm_"))
async def confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    key = data["key"]
    price = data["price"]
    service_name = SERVICES[key]["name"]

    # Уведомление владельцу
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        await bot.send_message(
            owner_id,
            f"🆕 НОВЫЙ ЗАКАЗ!\n"
            f"Пользователь: @{callback.from_user.username} (ID: {callback.from_user.id})\n"
            f"Услуга: {service_name}\nСумма: {price} ₽"
        )

    # Инструкция по оплате
    await callback.message.edit_text(
        f"Сумма: <b>{price} ₽</b>\n\n"
        f"📍 Переведите через СБП:\n"
        f" • Телефон: <code>{SBP_PHONE}</code>\n"
        f" • Получатель: <b>{OWNER_NAME}</b>\n\n"
        f"❗ В комментарии укажите: «Заказ №{callback.message.message_id}»\n\n"
        f"После оплаты нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я оплатил", callback_data="paid")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(OrderStates.awaiting_payment)

@dp.callback_query(F.data == "paid")
async def paid(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✅ Спасибо! Проверим платёж и начнём работу.")
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        await bot.send_message(owner_id, f"🔔 @{callback.from_user.username} заявил об оплате!")
    await state.clear()

@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Заказ отменён.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

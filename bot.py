import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# === Услуги с ПРИМЕРНЫМИ ценами ===
SERVICES = {
    "restoration": {"name": "Реставрация фото", "price_from": 500},
    "animation": {"name": "Оживление фото", "price_from": 400},
    "souvenirs": {"name": "Сувениры", "price_from": 300},
    "editing": {"name": "Обработка фотографий", "price_from": 250},
}

class OrderStates(StatesGroup):
    choosing_service = State()

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Начать", callback_data="start_order")]
    ])

def get_service_kb():
    buttons = [
        [InlineKeyboardButton(text=f"{v['name']} (от {v['price_from']} ₽)", callback_data=f"service_{k}")]
        for k, v in SERVICES.items()
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

@dp.message()
async def welcome(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Добро пожаловать в фотосервис!\nНажмите «Начать», чтобы оформить заказ.",
        reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "start_order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите услугу:", reply_markup=get_service_kb())
    await state.set_state(OrderStates.choosing_service)

@dp.callback_query(OrderStates.choosing_service, F.data.startswith("service_"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_key = callback.data.split("_")[1]
    if service_key not in SERVICES:
        await callback.answer("❌ Неверный выбор")
        return

    service = SERVICES[service_key]
    username = callback.from_user.username or "—"
    user_id = callback.from_user.id

    # Отправляем уведомление владельцу
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        msg = (
            f"🆕 НОВЫЙ ЗАКАЗ!\n"
            f"Пользователь: @{username} (ID: {user_id})\n"
            f"Услуга: {service['name']}\n"
            f"Примерная стоимость: от {service['price_from']} ₽"
        )
        await bot.send_message(owner_id, msg)

    # Автоматически возвращаем в начальное меню
    await callback.message.edit_text(
        "✅ Заказ принят! Мы свяжемся с вами в ближайшее время.\n\n"
        "Вы можете оформить ещё один заказ:",
        reply_markup=get_main_kb()
    )
    await state.clear()  # Сбрасываем состояние

@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Заказ отменён.\n\nНажмите «Начать», чтобы оформить новый заказ.",
        reply_markup=get_main_kb()
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

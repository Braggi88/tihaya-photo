import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# === Услуги с примерными ценами ===
SERVICES = {
    "restoration": {"name": "Реставрация фото", "price_from": 500},
    "animation": {"name": "Оживление фото", "price_from": 400},
    "souvenirs": {"name": "Сувениры", "price_from": 300},
    "editing": {"name": "Обработка фотографий", "price_from": 250},
}

class OrderStates(StatesGroup):
    choosing_service = State()
    waiting_phone = State()

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

def get_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

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

    service_name = SERVICES[service_key]["name"]
    price_from = SERVICES[service_key]["price_from"]

    await state.update_data(service_name=service_name, price_from=price_from)

    await callback.message.answer(
        "📞 Пожалуйста, укажите ваш номер телефона для связи.\n"
        "Вы можете:\n"
        "• Написать его вручную (например, +79123456789)\n"
        "• Нажать кнопку «📱 Отправить номер»",
        reply_markup=get_phone_kb()
    )
    await state.set_state(OrderStates.waiting_phone)

@dp.message(OrderStates.waiting_phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await _process_order(message, state, phone)

@dp.message(OrderStates.waiting_phone, F.text)
async def phone_from_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Простая проверка: минимум 10 цифр
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) < 10:
        await message.answer("❌ Некорректный номер. Попробуйте снова:")
        return
    await _process_order(message, state, phone)

async def _process_order(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    service_name = data["service_name"]
    price_from = data["price_from"]
    username = message.from_user.username or "—"
    user_id = message.from_user.id

    # Отправляем уведомление владельцу
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        msg = (
            f"🆕 НОВЫЙ ЗАКАЗ!\n"
            f"Пользователь: @{username} (ID: {user_id})\n"
            f"Телефон: <code>{phone}</code>\n"
            f"Услуга: {service_name}\n"
            f"Примерная стоимость: от {price_from} ₽"
        )
        await bot.send_message(owner_id, msg, parse_mode="HTML")

    # Возвращаем в начальное меню
    await message.answer(
        "✅ Заказ принят! Мы свяжемся с вами в ближайшее время.\n\n"
        "Вы можете оформить ещё один заказ:",
        reply_markup=get_main_kb()
    )
    await state.clear()

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

import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# === Услуги и ПРИМЕРНЫЕ цены (от ...) ===
SERVICES = {
    "restoration": {"name": "Реставрация фото", "price_from": 500},
    "animation": {"name": "Оживление фото", "price_from": 400},
    "souvenirs": {"name": "Сувениры", "price_from": 300},
    "editing": {"name": "Обработка фотографий", "price_from": 250},
}

class OrderStates(StatesGroup):
    choosing_service = State()
    waiting_comment = State()
    finished = State()

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Начать", callback_data="start_order")],
    ])

def get_service_kb():
    buttons = [
        [InlineKeyboardButton(text=f"{v['name']} (от {v['price_from']} ₽)", callback_data=f"service_{k}")]
        for k, v in SERVICES.items()
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_comment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])

def get_finish_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать ещё заказ", callback_data="start_order")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

# --- Обработчики ---
@dp.message()
async def any_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
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
    await state.update_data(
        service_key=service_key,
        service_name=service["name"],
        price_from=service["price_from"]
    )

    await callback.message.edit_text(
        "Отлично! Хотите оставить комментарий к заказу?\n"
        "(Например: «хочу на матовой бумаге», «срочно» и т.д.)\n\n"
        "Напишите сообщение или нажмите «Пропустить».",
        reply_markup=get_comment_kb()
    )
    await state.set_state(OrderStates.waiting_comment)

@dp.message(OrderStates.waiting_comment)
async def receive_comment(message: Message, state: FSMContext):
    comment = message.text
    data = await state.get_data()
    
    # Сохраняем заказ
    service_name = data["service_name"]
    price_from = data["price_from"]
    username = message.from_user.username or "—"
    user_id = message.from_user.id

    # Уведомление владельцу
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        msg = (
            f"🆕 НОВЫЙ ЗАКАЗ!\n"
            f"Пользователь: @{username} (ID: {user_id})\n"
            f"Услуга: {service_name}\n"
            f"Цена: от {price_from} ₽\n"
            f"Комментарий: {comment}"
        )
        await bot.send_message(owner_id, msg)

    await message.answer(
        "✅ Спасибо за заказ! Мы свяжемся с вами в ближайшее время.",
        reply_markup=get_finish_kb()
    )
    await state.set_state(OrderStates.finished)

@dp.callback_query(OrderStates.waiting_comment, F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service_name = data["service_name"]
    price_from = data["price_from"]
    username = callback.from_user.username or "—"
    user_id = callback.from_user.id

    # Уведомление владельцу
    owner_id = os.getenv("OWNER_CHAT_ID")
    if owner_id:
        msg = (
            f"🆕 НОВЫЙ ЗАКАЗ!\n"
            f"Пользователь: @{username} (ID: {user_id})\n"
            f"Услуга: {service_name}\n"
            f"Цена: от {price_from} ₽\n"
            f"Комментарий: —"
        )
        await bot.send_message(owner_id, msg)

    await callback.message.edit_text(
        "✅ Спасибо за заказ! Мы свяжемся с вами в ближайшее время.",
        reply_markup=get_finish_kb()
    )
    await state.set_state(OrderStates.finished)

@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Заказ отменён.\n\nНажмите «Начать», чтобы оформить новый заказ.",
        reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "start_order")
async def restart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await start_order(callback, state)

# --- Запуск ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

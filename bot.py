"""AI-консультант для фитнес-клуба "Атлет" на локальной Ollama"""
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import BOT_TOKEN, ADMIN_ID, GOOGLE_SHEETS_ID
from ai_client import get_ai_answer

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

chat_histories = {}


class BookingForm(StatesGroup):
    name = State()
    phone = State()
    service = State()


class ManagerForm(StatesGroup):
    question = State()


def get_sheets_client():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    return gspread.authorize(creds)


def save_dialog_to_sheets(user_id, username, question, answer):
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        sheet = spreadsheet.sheet1
        now = datetime.now()
        sheet.append_row([
            now.strftime("%d.%m.%Y"),
            now.strftime("%H:%M"),
            username or str(user_id),
            question,
            answer,
            str(user_id)
        ])
        print(f"✅ Диалог сохранён: {username or user_id}")
    except Exception as e:
        print(f"❌ Ошибка сохранения диалога: {e}")


def save_booking_to_sheets(data):
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        try:
            sheet = spreadsheet.worksheet("Заявки")
        except gspread.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title="Заявки", rows=100, cols=10)
            sheet.append_row(["Дата", "Время", "Имя", "Телефон", "Интерес", "Статус"])
        now = datetime.now()
        sheet.append_row([
            now.strftime("%d.%m.%Y"),
            now.strftime("%H:%M"),
            data['name'],
            data['phone'],
            data['service'],
            'Новая'
        ])
        print(f"✅ Заявка сохранена: {data['name']}")
    except Exception as e:
        print(f"❌ Ошибка сохранения заявки: {e}")


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 Задать вопрос"), KeyboardButton(text="📝 Оставить заявку")],
            [KeyboardButton(text="👨‍💼 Позвать менеджера"), KeyboardButton(text="ℹ️ О клубе")]
        ],
        resize_keyboard=True
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    chat_histories[message.from_user.id] = []
    username = message.from_user.username or message.from_user.first_name
    await message.answer(
        f"👋 Привет, {username}!\n\n"
        f"Я — AI-консультант фитнес-клуба 'Атлет' 💪\n\n"
        f"Могу рассказать о:\n"
        f"• абонементах и ценах\n"
        f"• групповых занятиях\n"
        f"• тренерах\n"
        f"• дополнительных услугах\n\n"
        f"Выбери действие или просто напиши вопрос 👇",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "💬 Задать вопрос")
async def ask_question(message: types.Message):
    await message.answer(
        "💬 Напиши свой вопрос!\n\n"
        "Например:\n"
        "• Сколько стоит абонемент?\n"
        "• Какие есть групповые занятия?\n"
        "• Кто ваши тренеры?",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(F.text == "📝 Оставить заявку")
async def start_booking(message: types.Message, state: FSMContext):
    await message.answer("📝 Отлично! 👤 Как вас зовут?",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BookingForm.name)


@dp.message(BookingForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📱 Введите ваш номер телефона:")
    await state.set_state(BookingForm.phone)


@dp.message(BookingForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏋️ Пробная тренировка", callback_data="service_trial")],
        [InlineKeyboardButton(text="💳 Купить абонемент", callback_data="service_membership")],
        [InlineKeyboardButton(text="👨‍🏫 Персональная тренировка", callback_data="service_personal")],
        [InlineKeyboardButton(text="🤔 Другое", callback_data="service_other")],
    ])
    await message.answer("🎯 Что вас интересует?", reply_markup=keyboard)
    await state.set_state(BookingForm.service)


@dp.callback_query(BookingForm.service)
async def process_service(callback: types.CallbackQuery, state: FSMContext):
    service_map = {
        "service_trial": "Пробная тренировка",
        "service_membership": "Покупка абонемента",
        "service_personal": "Персональная тренировка",
        "service_other": "Другое",
    }
    service = service_map.get(callback.data, "Другое")
    await state.update_data(service=service)
    data = await state.get_data()

    text = (
        f"✅ Заявка принята!\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🎯 Интерес: {data['service']}\n\n"
        f"Менеджер свяжется с вами в течение 15 минут! 💪"
    )
    await callback.message.answer(text, reply_markup=get_main_keyboard())

    try:
        admin_text = (
            f"🆕 Новая заявка!\n\n"
            f"👤 {data['name']}\n"
            f"📱 {data['phone']}\n"
            f"🎯 {data['service']}\n"
            f"👤 @{callback.from_user.username or callback.from_user.id}"
        )
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    save_booking_to_sheets(data)
    await state.clear()
    await callback.answer()


@dp.message(F.text == "👨‍💼 Позвать менеджера")
async def call_manager(message: types.Message, state: FSMContext):
    await message.answer(
        "👨‍💼 Напишите ваш вопрос — менеджер ответит лично.\n\n"
        "Или позвоните: +7 (999) 555-12-34",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(ManagerForm.question)


@dp.message(ManagerForm.question)
async def process_manager_question(message: types.Message, state: FSMContext):
    await state.clear()
    username = message.from_user.username or message.from_user.first_name
    try:
        admin_text = (
            f"🔔 Клиент зовёт менеджера!\n\n"
            f"👤 {username}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"💬 Вопрос: {message.text}"
        )
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
    await message.answer(
        "✅ Передал ваш вопрос менеджеру!\nОн ответит в течение 15 минут. 💪",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "ℹ️ О клубе")
async def about_club(message: types.Message):
    await message.answer(
        "🏋️ Фитнес-клуб 'Атлет'\n\n"
        "📍 Адрес: ул. Спортивная, 45\n"
        "📞 Телефон: +7 (999) 555-12-34\n"
        "🕐 Пн-Пт: 06:00-23:00\n"
        "🕐 Сб-Вс: 08:00-22:00\n\n"
        "🎁 Первая тренировка — БЕСПЛАТНО!",
        reply_markup=get_main_keyboard()
    )


@dp.message()
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    user_message = message.text

    if user_message.startswith('/'):
        return

    history = chat_histories.get(user_id, [])
    await bot.send_chat_action(message.chat.id, "typing")

    answer = await get_ai_answer(user_message, history)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": answer})
    chat_histories[user_id] = history[-10:]

    await message.answer(answer, reply_markup=get_main_keyboard())

    asyncio.create_task(
        asyncio.to_thread(save_dialog_to_sheets, user_id, username, user_message, answer)
    )


async def main():
    print("🤖 AI-консультант 'Атлет' запущен!")
    print(f"🧠 Модель: {OLLAMA_MODEL if 'OLLAMA_MODEL' in globals() else 'llama3.1:8b'}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    from config import OLLAMA_MODEL
    asyncio.run(main())
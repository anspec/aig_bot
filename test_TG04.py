#import aiosqlite
import requests
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import TG_TOKEN, DADATA_TOKEN, DATA_SECRET_KEY
from dadata import Dadata

import datetime as dt
from unittest import mock
import httpx
from dadata.asynchr import DadataClient, CleanClient, ProfileClient, SuggestClient

# Создаем роутер
router = Router()

# --- Классы для FSM ---
class IpForm(StatesGroup):
    waiting_for_ip = State()

class AddressForm(StatesGroup):
    waiting_for_address = State()

class CadNumberForm(StatesGroup):
    waiting_for_cad_number = State()

class AddressToCadForm(StatesGroup):
    waiting_for_address = State()

# --- Настройка DaData API ---
DADATA_URL_IP = "https://suggestions.dadata.ru/suggestions/api/4_1/iplocate/{ip}"
DADATA_URL_CLEAN_ADDR = "https://cleaner.dadata.ru/api/v1/clean/address"
DADATA_URL_FIND_ADDR = "https://suggestions.dadata.ru/suggestions/api/4_1/json/findById/address"
DADATA_URL_CADASTRE_CLEAN = "https://cleaner.dadata.ru/api/v1/clean/cadastre"

HEADERS = {
    "Authorization": f"Token {DADATA_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# --- Команда /ip_town ---
@router.message(Command("ip_town"))
async def cmd_ip_town(message: Message, state: FSMContext):
    await message.answer("Введите IP-адрес:")
    await state.set_state(IpForm.waiting_for_ip)


@router.message(IpForm.waiting_for_ip, F.text)
async def process_ip(message: Message, state: FSMContext):
    ip = message.text.strip()
    try:
        dadata = Dadata(DADATA_TOKEN, DATA_SECRET_KEY  )
        result = dadata.iplocate(ip)
        #await message.answer(f"📍 result по IP {ip}: <b>{result}</b>", parse_mode="HTML")

        if result and "data" in result and result["data"]:
            city = result["data"]["city"]
            await message.answer(f"📍 Город по IP {ip}: <b>{city}</b>", parse_mode="HTML")
        else:
            await message.answer("❌ Не удалось определить город по указанному IP.")
    except requests.exceptions.ConnectionError:
        await message.answer("❌ Ошибка подключения к сервису DaData. Проверьте интернет-соединение.")
    except requests.exceptions.Timeout:
        await message.answer("❌ Время ожидания ответа от DaData истекло.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            await message.answer("❌ Ошибка авторизации DaData: неверный токен.")
        elif e.response.status_code == 429:
            await message.answer("❌ Слишком много запросов к DaData. Попробуйте позже.")
        else:
            await message.answer(f"❌ HTTP ошибка: {e.response.status_code}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при определении города: {e}")
    finally:
        await state.clear()


# --- Добавлена команда /help ---
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start — показать меню с кнопками «Привет» и «Пока»\n"
        "/links — показать кнопки с ссылками на новости, музыку и видео\n"
        "/dynamic — показать кнопку «Показать больше», которая превращается в две опции\n"
        "/ip_town — определить город по IP-адресу\n"
        "/help — показать это сообщение"
    )
    await message.answer(help_text)

# --- Задание 1: Простое меню с кнопками ---
@router.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Привет", callback_data="hello")],
        [InlineKeyboardButton(text="Пока", callback_data="goodbye")]
    ])
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(F.data == "hello")
async def callback_hello(call: CallbackQuery):
    username = call.from_user.first_name
    await call.message.answer(f"Привет, {username}!")
    await call.answer()

@router.callback_query(F.data == "goodbye")
async def callback_goodbye(call: CallbackQuery):
    username = call.from_user.first_name
    await call.message.answer(f"До свидания, {username}!")
    await call.answer()


# --- Задание 2: Кнопки с URL-ссылками ---
@router.message(Command("links"))
async def cmd_links(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новости", url="https://news.yandex.ru")],
        [InlineKeyboardButton(text="Музыка", url="https://music.yandex.ru")],
        [InlineKeyboardButton(text="Видео", url="https://www.youtube.com")]
    ])
    await message.answer("Выберите ресурс:", reply_markup=keyboard)


# --- Задание 3: Динамическое изменение клавиатуры ---
@router.message(Command("dynamic"))
async def cmd_dynamic(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать больше", callback_data="show_more")]
    ])
    await message.answer("Нажмите кнопку:", reply_markup=keyboard)

@router.callback_query(F.data == "show_more")
async def callback_show_more(call: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опция 1", callback_data="option_1")],
        [InlineKeyboardButton(text="Опция 2", callback_data="option_2")]
    ])
    await call.message.edit_text("Выберите опцию:", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data == "option_1")
async def callback_option_1(call: CallbackQuery):
    await call.message.answer("Вы выбрали: Опция 1")
    await call.answer()

@router.callback_query(F.data == "option_2")
async def callback_option_2(call: CallbackQuery):
    await call.message.answer("Вы выбрали: Опция 2")
    await call.answer()


# --- Запуск бота ---
async def main():
    bot = Bot(token=TG_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
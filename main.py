import asyncio
import random
import requests #Для выполнения HTTP-запросов к внешним API

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import TG_TOKEN, OPENWEATHER_API_KEY


bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет, я бот!")

@dp.message(Command('help'))
async def help(message: Message):
    await message.answer("Этот бот отвечает на команды: \n "
                         "/start - начало диалога \n "
                         "/help - помощь \n"
                         "/photo - случайное фото \n"
                         "/weather - прогноз погоды")

@dp.message(Command('weather'))
async def weather(message: Message):
    city = 'Moscow'
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    try:
        response = requests.get(url)  # Отправка запроса
        data = response.json()  # Парсинг ответа в словарь
        if response.status_code == 200:  # Проверка на успешность запроса
            weather_info = (
                f" Погода в г.{city}:\n"
                f" Температура:  {data['main']['temp']} °C\n"
                f" Состояние:  {data['weather'][0]['description']} \n"
                f" Влажность:  {data['main']['humidity']} %\n"
                f" Ветер:  {data['wind']['speed']} м/с"
            )
        else:
            if response.status_code == 404:
                weather_info = "Город не найден"
            else:
                weather_info = f"Ошибка при получении информации о погоде: {response.status_code}"
    except Exception as e:
        weather_info = f"Ошибка при получении информации о погоде: {e}"
    await message.answer(weather_info)

@dp.message(F.text == "что такое ИИ?")
async def aitext(message: Message):
    await message.answer('ИИ - это искусственный интеллект')

@dp.message(F.photo)
async def react_photo(message: Message):
    list = ['Ого, какая фотка!',
            'Непонятно, что это такое',
            'Не отправляй мне такое больше'
    ]
    rand_answ = random.choice(list)
    await message.answer(rand_answ)

@dp.message(Command('photo'))
async def photo(message: Message):
    list = ['https://ru.freepik.com/free-photo/vertical-shot-leopard-its-habitat-safari-okavanga-delta-botswana_24345392.htm#position=4',
            'https://ru.freepik.com/premium-photo/selective-focus-shot-mother-monkey-holding-baby-monkey-its-warm-embrace_23835238.htm#position=2',
            'https://ru.freepik.com/free-photo/vertical-shot-cute-cat-background-field_24345412.htm#position=20'
            ]
    rand_photo = random.choice(list)
    await message.answer_photo(photo=rand_photo, caption='Это интересная фотка!')


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
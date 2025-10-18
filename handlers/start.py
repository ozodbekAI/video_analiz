from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.client import get_main_menu_keyboard
from database.crud import get_user, create_user
from utils.texts import START_MESSAGE

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await create_user(message.from_user.id, message.from_user.username)
    await message.answer(START_MESSAGE, reply_markup=get_main_menu_keyboard())
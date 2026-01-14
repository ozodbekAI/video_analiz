from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.client import get_language_keyboard, get_main_menu_keyboard
from database.crud import get_user, create_user, update_user_language
from utils.texts import START_MESSAGE, WELCOME_MESSAGE
from callbacks.menu import MenuCallback
from states.common import CommonFSM

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    
    if not user:
        await create_user(message.from_user.id, message.from_user.username)
        await state.set_state(CommonFSM.choosing_language)
        await message.answer(WELCOME_MESSAGE, reply_markup=get_language_keyboard())
    else:
        await message.answer(START_MESSAGE, reply_markup=get_main_menu_keyboard())


@router.callback_query(MenuCallback.filter(F.action == "select_language"))
async def select_language_handler(query: CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    language = callback_data.category
    
    await update_user_language(query.from_user.id, language)
    
    current_state = await state.get_state()
    if current_state == CommonFSM.choosing_language:
        await state.clear()
        
        if language != "ru":
            await query.message.edit_text(
                "🚧 This language is under development. Switching to Russian.\n\n"
                "🚧 Este idioma está em desenvolvimento. Mudando para russo.\n\n"
                "🚧 Cette langue est en développement. Passage au russe."
            )
            await query.message.answer(START_MESSAGE, reply_markup=get_main_menu_keyboard())
        else:
            await query.message.edit_text(START_MESSAGE, reply_markup=get_main_menu_keyboard())
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

async def safe_edit_text(
    query: CallbackQuery, 
    text: str, 
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = None
):
    try:
        if query.message.text or query.message.caption:
            await query.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.message.delete()
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        elif "there is no text in the message" in str(e).lower():
            try:
                await query.message.delete()
            except:
                pass
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        print(f"Error in safe_edit_text: {e}")
        await query.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
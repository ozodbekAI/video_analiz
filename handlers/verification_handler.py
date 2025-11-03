from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hcode
from services.verifiaction_service import VerificationService
from services.youtube_service import get_channel_description
from keyboards.client import get_main_menu_keyboard

router = Router()


class VerificationFSM(StatesGroup):
    waiting_for_verification_check = State()


def get_verification_check_keyboard(attempt_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я разместил код, проверить", callback_data=f"verify:check:{attempt_id}")
    builder.button(text="🚫 Отменить", callback_data="verify:cancel")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "verify:start_from_analysis")
async def start_verification_from_analysis_short(query: CallbackQuery, state: FSMContext):
    from handlers.analysis import pending_verification_channels
    
    user_id = query.from_user.id
    
    channel_url = pending_verification_channels.get(user_id)
    
    if not channel_url:
        await query.answer("❌ Ошибка: канал не найден. Попробуйте снова.", show_alert=True)
        await query.message.edit_text(
            "❌ Произошла ошибка. Попробуйте начать анализ заново.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    state_data = await state.get_data()
    video_url = state_data.get('pending_video_url')
    analysis_category = state_data.get('pending_analysis_category')
    analysis_type = state_data.get('pending_analysis_type')
    
    try:
        verification_code, attempt_id = await VerificationService.initiate_verification(
            user_id=user_id,
            channel_url=channel_url
        )
        
        await state.update_data(
            attempt_id=attempt_id,
            verification_code=verification_code,
            channel_url=channel_url,
            check_count=0,
            pending_video_url=video_url,
            pending_analysis_category=analysis_category,
            pending_analysis_type=analysis_type
        )
        await state.set_state(VerificationFSM.waiting_for_verification_check)
        
        escaped_code = hcode(verification_code)
        
        await query.message.edit_text(
            f"🔐 <b>ПОДТВЕРЖДЕНИЕ КАНАЛА</b>\n\n"
            f"<b>Ваш код:</b>\n{escaped_code}\n\n"
            f"📋 <b>Инструкция:</b>\n\n"
            f"1️⃣ Скопируйте код выше\n"
            f"2️⃣ Откройте YouTube Studio\n"
            f"3️⃣ Настройки → Канал → Основная информация\n"
            f"4️⃣ Вставьте код в \"Описание канала\"\n"
            f"5️⃣ Сохраните изменения\n"
            f"6️⃣ Нажмите \"Я разместил код, проверить\"\n\n"
            f"⏱ Код действителен 24 часа\n\n"
            f"<i>После подтверждения анализ начнется автоматически.</i>",
            reply_markup=get_verification_check_keyboard(attempt_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data.startswith("verify:check:"))
async def check_verification_handler(query: CallbackQuery, state: FSMContext):
    attempt_id = int(query.data.split(":")[-1])
    
    await query.answer("⏳ Проверяется...", show_alert=False)
    
    state_data = await state.get_data()
    check_count = state_data.get('check_count', 0) + 1
    await state.update_data(check_count=check_count)
    
    from datetime import datetime
    check_time = datetime.now().strftime("%H:%M:%S")
    
    try:
        pending = await VerificationService.get_pending_verification(query.from_user.id)
        
        if not pending or pending['id'] != attempt_id:
            try:
                await query.message.edit_text(
                    f"❌ <b>ВЕРИФИКАЦИЯ НЕ НАЙДЕНА</b>\n\n"
                    f"Код истек или был отменен.",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
            except Exception:
                await query.message.answer(
                    f"❌ Код истек или был отменен.",
                    reply_markup=get_main_menu_keyboard()
                )
            await state.clear()
            return
        
        channel_url = pending['channel_url']
        verification_code = pending['code']
        
        try:
            channel_description = await get_channel_description(channel_url)
        except Exception as e:
            try:
                await query.message.edit_text(
                    f"❌ <b>ОШИБКА</b> (#{check_count})\n\n"
                    f"Не удалось получить данные канала.\n\n"
                    f"{str(e)}\n\n"
                    f"Попробуйте через минуту.",
                    reply_markup=get_verification_check_keyboard(attempt_id),
                    parse_mode="HTML"
                )
            except Exception:
                await query.message.answer(
                    f"❌ Ошибка получения данных канала.",
                    reply_markup=get_verification_check_keyboard(attempt_id)
                )
            return
        
        success, message_text = await VerificationService.check_code_in_description(
            attempt_id=attempt_id,
            channel_description=channel_description
        )
        
        if success:
            video_url = state_data.get('pending_video_url')
            analysis_category = state_data.get('pending_analysis_category')
            analysis_type = state_data.get('pending_analysis_type')
            
            try:
                await query.message.edit_text(
                    f"✅ <b>КАНАЛ ПОДТВЕРЖДЕН!</b>\n\n"
                    f"📊 Канал: {hcode(channel_url)}\n\n"
                    f"🚀 Запускаем анализ...",
                    parse_mode="HTML"
                )
            except Exception:
                await query.message.answer(
                    f"✅ <b>КАНАЛ ПОДТВЕРЖДЕН!</b>\n\n"
                    f"🚀 Запускаем анализ...",
                    parse_mode="HTML"
                )
            
            await state.clear()
            
            if video_url and analysis_category and analysis_type:
                from handlers.analysis import run_analysis_task
                import asyncio

                task = asyncio.create_task(
                    run_analysis_task(
                        query.from_user.id,
                        query.message,
                        video_url,
                        analysis_category,
                        analysis_type
                    )
                )
                
                from handlers.analysis import user_analysis_locks
                user_analysis_locks[query.from_user.id] = task
                
                def cleanup(t):
                    if query.from_user.id in user_analysis_locks:
                        del user_analysis_locks[query.from_user.id]
                
                task.add_done_callback(cleanup)
            else:
                await query.message.answer(
                    "Теперь отправьте URL видео для анализа.",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            try:
                await query.message.edit_text(
                    f"❌ <b>КОД НЕ НАЙДЕН</b> (#{check_count}, {check_time})\n\n"
                    f"<b>Код:</b> {hcode(verification_code)}\n\n"
                    f"<b>Проверьте:</b>\n"
                    f"• Код в описании канала\n"
                    f"• Изменения сохранены\n"
                    f"• Прошло 1-2 минуты\n\n"
                    f"Попробуйте снова.",
                    reply_markup=get_verification_check_keyboard(attempt_id),
                    parse_mode="HTML"
                )
            except Exception:
                await query.message.answer(
                    f"❌ Код не найден (#{check_count})\n\n"
                    f"Код: {hcode(verification_code)}",
                    reply_markup=get_verification_check_keyboard(attempt_id),
                    parse_mode="HTML"
                )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        try:
            await query.message.edit_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception:
            await query.message.answer(
                f"❌ Ошибка: {str(e)}",
                reply_markup=get_main_menu_keyboard()
            )
        await state.clear()


@router.callback_query(F.data == "verify:cancel")
async def cancel_verification_handler(query: CallbackQuery, state: FSMContext):
    await VerificationService.cancel_pending_verification(query.from_user.id)
    await state.clear()
    
    await query.message.edit_text(
        "🚫 Верификация отменена.",
        reply_markup=get_main_menu_keyboard()
    )
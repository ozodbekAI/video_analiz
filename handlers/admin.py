import io
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from callbacks.admin import AdminCallback
from states.admin import AdminFSM
from keyboards.admin import (
    get_admin_menu_keyboard,
    get_back_keyboard, 
    get_prompt_category_keyboard, 
    get_prompt_type_keyboard, 
    get_advanced_subtype_keyboard, 
    get_prompts_keyboard,
    get_stats_keyboard,
    get_user_management_keyboard  # YANGI
)
from database.crud import (
    get_prompts, create_prompt, update_prompt, delete_prompt,
    get_total_users, get_total_videos, get_total_ai_requests,
    get_users_today, get_videos_today, get_ai_requests_today,
    get_analysis_type_stats, get_top_active_users, get_recent_videos,
    get_average_comments_per_video, get_prompts_count,
    get_user_by_id, set_user_limit, reset_user_analyses  # YANGI
)
from utils.texts import ADMIN_MENU, PROMPTS_LIST, ENTER_PROMPT_NAME, ENTER_PROMPT_TEXT, PROMPT_ADDED, PROMPT_UPDATED
from utils.helpers import safe_edit_text
from datetime import datetime

router = Router()

@router.message(F.text == "/admin")
async def admin_menu_handler(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ У вас нет прав для использования этой команды!")
        return
    
    await message.answer(ADMIN_MENU, reply_markup=get_admin_menu_keyboard())


# ============ LIMIT BOSHQARUV ============

@router.callback_query(AdminCallback.filter(F.action == "manage_users"))
async def manage_users_handler(query: CallbackQuery, state: FSMContext):
    """User limitlarini boshqarish"""
    await query.message.edit_text(
        "👥 <b>УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ</b>\n\n"
        "Отправьте User ID для управления его лимитами.\n"
        "Пример: <code>123456789</code>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminFSM.waiting_for_user_id)


@router.message(AdminFSM.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    """User ID qabul qilish"""
    try:
        user_id = int(message.text.strip())
        user = await get_user_by_id(user_id)
        
        if not user:
            await message.answer(
                f"❌ Пользователь с ID <code>{user_id}</code> не найден",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )
            await state.clear()
            return
        
        await state.update_data(target_user_id=user_id)
        
    
        registration_date = user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'
        last_reset = user.last_reset_date.strftime('%d.%m.%Y') if user.last_reset_date else 'Никогда'
        
        await message.answer(
            f"👤 <b>Пользователь найден</b>\n\n"
            f"🆔 ID: <code>{user.user_id}</code>\n"
            f"👤 Username: {user.username or 'Не указан'}\n"
            f"📊 Использовано: {user.analyses_used}/{user.analyses_limit}\n"
            f"📅 Регистрация: {registration_date}\n"
            f"🔄 Последний сброс: {last_reset}\n\n"
            f"Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_user_management_keyboard()
        )
        await state.set_state(AdminFSM.managing_user)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите числовой User ID.",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()


@router.callback_query(AdminFSM.managing_user, AdminCallback.filter(F.action == "set_limit"))
async def set_limit_handler(query: CallbackQuery, state: FSMContext):
    """Limit o'rnatish"""
    await query.message.edit_text(
        "📊 <b>УСТАНОВКА ЛИМИТА</b>\n\n"
        "Введите новый лимит анализов для пользователя.\n"
        "Пример: <code>10</code>",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_limit)


@router.message(AdminFSM.waiting_for_limit)
async def process_new_limit(message: Message, state: FSMContext):
    """Yangi limitni qabul qilish"""
    try:
        new_limit = int(message.text.strip())
        
        if new_limit < 0:
            await message.answer("❌ Лимит не может быть отрицательным")
            return
        
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        await set_user_limit(target_user_id, new_limit)
        
        await message.answer(
            f"✅ Лимит успешно установлен: <code>{new_limit}</code> анализов",
            parse_mode="HTML",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число.")


@router.callback_query(AdminFSM.managing_user, AdminCallback.filter(F.action == "reset_usage"))
async def reset_usage_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    await reset_user_analyses(target_user_id)
    
    await query.message.edit_text(
        f"✅ Использование сброшено до 0\n\n"
        f"Пользователь <code>{target_user_id}</code> может снова использовать свой лимит.",
        parse_mode="HTML",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()



@router.callback_query(AdminCallback.filter(F.action == "view_stats"))
async def view_stats_handler(query: CallbackQuery):
    """Statistikani ko'rsatish"""
    try:
        import asyncio
        
        total_users, total_videos, total_ai_requests = await asyncio.gather(
            get_total_users(),
            get_total_videos(),
            get_total_ai_requests()
        )
        
        users_today, videos_today, ai_today = await asyncio.gather(
            get_users_today(),
            get_videos_today(),
            get_ai_requests_today()
        )
        
        prompts_count = await get_prompts_count()
        avg_comments = await get_average_comments_per_video()
        analysis_stats = await get_analysis_type_stats()
        
        stats_text = f"""📊 <b>СТАТИСТИКА БОТА</b>

<b>👥 ПОЛЬЗОВАТЕЛИ</b>
Всего: <code>{total_users}</code> | Сегодня: <code>{users_today}</code>

<b>📹 ВИДЕО</b>
Всего: <code>{total_videos}</code> | Сегодня: <code>{videos_today}</code>
Сред. комментариев: <code>{avg_comments}</code>

<b>🤖 AI ЗАПРОСЫ</b>
Всего: <code>{total_ai_requests}</code> | Сегодня: <code>{ai_today}</code>
"""
        
        if analysis_stats:
            stats_text += "\n<b>📝 ТИПЫ АНАЛИЗА</b>\n"
            analysis_names = {
                'simple': '⛏️ Простой',
                'advanced': '⚙️ Углубленный',
                'synthesis': '🔄 Синтез'
            }
            
            for analysis_type in ['simple', 'advanced', 'synthesis']:
                if analysis_type in analysis_stats:
                    count = analysis_stats[analysis_type]
                    display_name = analysis_names.get(analysis_type, analysis_type)
                    stats_text += f"{display_name}: <code>{count}</code>\n"
        
        stats_text += f"\n<b>📋 ПРОМПТЫ:</b> <code>{prompts_count}</code>"
        stats_text += f"\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        await safe_edit_text(query, stats_text, reply_markup=get_stats_keyboard(), parse_mode='HTML')
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        await query.message.edit_text(
            f"❌ Ошибка загрузки статистики\n\n{str(e)[:100]}",
            reply_markup=get_stats_keyboard()
        )


@router.callback_query(AdminCallback.filter(F.action == "top_users"))
async def top_users_handler(query: CallbackQuery):
    try:
        top_users = await get_top_active_users(limit=10)
        
        if not top_users:
            await query.message.edit_text(
                "Пока нет активных пользователей",
                reply_markup=get_stats_keyboard()
            )
            return
        
        text = "🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
        
        medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        for idx, (user_id, username, video_count) in enumerate(top_users):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            username_display = (username[:15] + "..." if username and len(username) > 15 else username) or f"User_{user_id}"
            text += f"{medal} {username_display} - <code>{video_count}</code>\n"
        
        text += f"\n🕐 {datetime.now().strftime('%H:%M')}"
        
        await query.message.edit_text(text, parse_mode='HTML', reply_markup=get_stats_keyboard())
    
    except Exception as e:
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)[:50]}",
            reply_markup=get_stats_keyboard()
        )


@router.callback_query(AdminCallback.filter(F.action == "recent_videos"))
async def recent_videos_handler(query: CallbackQuery):
    try:
        recent_videos = await get_recent_videos(limit=8)
        
        if not recent_videos:
            await query.message.edit_text(
                "Пока нет проанализированных видео",
                reply_markup=get_stats_keyboard()
            )
            return
        
        text = "📹 <b>ПОСЛЕДНИЕ АНАЛИЗЫ</b>\n\n"
        
        for video, username in recent_videos:
            username_display = (username[:12] + "..." if username and len(username) > 12 else username) or f"User_{video.user_id}"
            video_id = video.video_url.split('/')[-1].split('?')[0][:11]
            time_ago = datetime.now(video.processed_at.tzinfo) - video.processed_at
            if time_ago.days > 0:
                time_str = f"{time_ago.days}д"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600}ч"
            else:
                time_str = f"{time_ago.seconds // 60}м"
            
            text += f"👤 {username_display} | 🎬 {video_id} | ⏰ {time_str}\n"
        
        text += f"\n🕐 {datetime.now().strftime('%H:%M')}"
        
        await query.message.edit_text(text, parse_mode='HTML', reply_markup=get_stats_keyboard())
    
    except Exception as e:
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)[:50]}",
            reply_markup=get_stats_keyboard()
        )



@router.callback_query(AdminCallback.filter(F.action == "view_prompts"))
async def view_prompts_handler(query: CallbackQuery):
    await query.message.edit_text("Выберите категорию:", reply_markup=get_prompt_category_keyboard(add_mode=False))


@router.callback_query(AdminCallback.filter(F.action == "select_category"))
async def select_category_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    category = callback_data.category
    await state.update_data(category=category)
    await query.message.edit_text(f"Категория: {category}. Выберите тип анализа:", reply_markup=get_prompt_type_keyboard(add_mode=False))


@router.callback_query(AdminCallback.filter(F.action == "select_type"))
async def select_type_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    analysis_type = callback_data.analysis_type
    data = await state.get_data()
    category = data.get('category', 'my')
    
    if analysis_type == "simple":
        prompts = await get_prompts(category=category, analysis_type="simple")
        message_text = PROMPTS_LIST + "\n".join([f"{p.id}: {p.name}" for p in prompts])
        await query.message.edit_text(message_text, reply_markup=get_prompts_keyboard(prompts, "simple", category))
    elif analysis_type == "advanced":
        await query.message.edit_text("Выберите подтип для расширенного анализа:", reply_markup=get_advanced_subtype_keyboard(category, add_mode=False))


@router.callback_query(AdminCallback.filter(F.action == "select_subtype"))
async def select_subtype_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    subtype = callback_data.subtype
    data = await state.get_data()
    category = data.get('category', 'my')
    analysis_type = "advanced" if subtype == "advanced" else "synthesis"
    
    prompts = await get_prompts(category=category, analysis_type=analysis_type)
    message_text = PROMPTS_LIST + "\n".join([f"{p.id}: {p.name}" for p in prompts])
    await query.message.edit_text(message_text, reply_markup=get_prompts_keyboard(prompts, analysis_type, category))


@router.callback_query(AdminCallback.filter(F.action == "add_prompt"))
async def add_prompt_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text("Выберите категорию для нового промпта:", reply_markup=get_prompt_category_keyboard(add_mode=True))
    await state.set_state(AdminFSM.waiting_for_category)


@router.callback_query(AdminCallback.filter(F.action == "add_select_category"))
async def process_add_category(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    await state.update_data(category=callback_data.category)
    await query.message.edit_text("Выберите тип анализа:", reply_markup=get_prompt_type_keyboard(add_mode=True))
    await state.set_state(AdminFSM.waiting_for_type)


@router.callback_query(AdminCallback.filter(F.action == "add_select_type"))
async def process_add_type(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    analysis_type = callback_data.analysis_type
    await state.update_data(analysis_type=analysis_type)
    
    if analysis_type == "advanced":
        await query.message.edit_text("Выберите подтип (предыдущие или финальный):", reply_markup=get_advanced_subtype_keyboard(add_mode=True))
        await state.set_state(AdminFSM.waiting_for_subtype)
    else:
        await query.message.edit_text(ENTER_PROMPT_NAME)
        await state.set_state(AdminFSM.waiting_for_prompt_name)


@router.callback_query(AdminCallback.filter(F.action == "add_select_subtype"))
async def process_add_subtype(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    subtype = callback_data.subtype
    await state.update_data(subtype=subtype, analysis_type="advanced" if subtype == "advanced" else "synthesis")
    await query.message.edit_text(ENTER_PROMPT_NAME)
    await state.set_state(AdminFSM.waiting_for_prompt_name)


@router.message(AdminFSM.waiting_for_prompt_name)
async def process_prompt_name(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(prompt_name=message.text.strip())
        await message.answer("Введите текст промпта (или отправьте .txt файл):")
        await state.set_state(AdminFSM.waiting_for_prompt_text)
    else:
        await message.answer("Пожалуйста, введите имя промпта текстом.")


@router.message(AdminFSM.waiting_for_prompt_text)
async def process_prompt_text(message: Message, state: FSMContext, bot: Bot):
    prompt_text = None
    
    if message.text:
        prompt_text = message.text.strip()
    elif message.document:
        if message.document.mime_type != 'text/plain':
            await message.answer("Пожалуйста, отправьте только .txt файл (text/plain).")
            return
        
        file_io = io.BytesIO()
        try:
            await bot.download(message.document, destination=file_io)
            file_io.seek(0)
            prompt_text = file_io.read().decode('utf-8').strip()
        except Exception as e:
            await message.answer(f"Ошибка чтения файла: {str(e)}")
            return
        finally:
            file_io.close()
    else:
        await message.answer("Пожалуйста, отправьте текст или .txt файл.")
        return
    
    if not prompt_text:
        await message.answer("Текст промпта пустой. Попробуйте снова.")
        return
    
    data = await state.get_data()
    analysis_type = data.get('analysis_type', 'simple')
    category = data.get('category', 'my')
    prompt_name = data.get('prompt_name', 'Unnamed')
    
    await create_prompt(prompt_name, prompt_text, analysis_type, category)
    await message.answer(PROMPT_ADDED, reply_markup=get_admin_menu_keyboard())
    await state.clear()


@router.callback_query(AdminCallback.filter(F.action == "update_prompt"))
async def update_prompt_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    await state.update_data(prompt_id=callback_data.prompt_id)
    await query.message.edit_text("Введите новый текст промпта (или отправьте .txt файл):")
    await state.set_state(AdminFSM.waiting_for_update_text)


@router.message(AdminFSM.waiting_for_update_text)
async def process_update_text(message: Message, state: FSMContext, bot: Bot):
    prompt_text = None
    
    if message.text:
        prompt_text = message.text.strip()
    elif message.document:
        if message.document.mime_type != 'text/plain':
            await message.answer("Пожалуйста, отправьте только .txt файл (text/plain).")
            return
        
        file_io = io.BytesIO()
        try:
            await bot.download(message.document, destination=file_io)
            file_io.seek(0)
            prompt_text = file_io.read().decode('utf-8').strip()
        except Exception as e:
            await message.answer(f"Ошибка чтения файла: {str(e)}")
            return
        finally:
            file_io.close()
    else:
        await message.answer("Пожалуйста, отправьте текст или .txt файл.")
        return
    
    if not prompt_text:
        await message.answer("Текст пустой.")
        return
    
    data = await state.get_data()
    await update_prompt(data['prompt_id'], prompt_text)
    await message.answer(PROMPT_UPDATED, reply_markup=get_admin_menu_keyboard())
    await state.clear()


@router.callback_query(AdminCallback.filter(F.action == "delete_prompt"))
async def delete_prompt_handler(query: CallbackQuery, callback_data: AdminCallback):
    await delete_prompt(callback_data.prompt_id)
    await query.answer("Промпт удалён!", show_alert=True)
    await view_prompts_handler(query)


@router.callback_query(AdminCallback.filter(F.action == "back"))
async def back_to_admin_menu_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text(ADMIN_MENU, reply_markup=get_admin_menu_keyboard())
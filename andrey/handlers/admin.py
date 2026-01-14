import io
import json
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, Document, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.admin import AdminCallback
from services.sample_report_service import SampleReportsService
from services.youtube_service import extract_video_id
from services.pdf_generator import generate_pdf
from states.admin import AdminFSM
from keyboards.admin import (
    get_admin_menu_keyboard,
    get_back_keyboard,
    get_evolution_step_keyboard, 
    get_prompt_category_keyboard, 
    get_prompt_type_keyboard, 
    get_advanced_subtype_keyboard, 
    get_prompts_keyboard,
    get_sample_reports_keyboard,
    get_stats_keyboard,
    get_user_management_keyboard
)
from database.crud import (
    get_prompts, create_prompt, update_prompt, delete_prompt,
    get_total_users, get_total_videos, get_total_ai_requests,
    get_users_today, get_videos_today, get_ai_requests_today,
    get_analysis_type_stats, get_top_active_users, get_recent_videos,
    get_average_comments_per_video, get_prompts_count,
    get_user_by_id, set_user_limit, reset_user_analyses
)
from utils.texts import ADMIN_MENU, PROMPTS_LIST, ENTER_PROMPT_NAME, ENTER_PROMPT_TEXT, PROMPT_ADDED, PROMPT_UPDATED
from utils.helpers import safe_edit_text
from datetime import datetime
from pathlib import Path
import os

router = Router()

@router.message(F.text == "/admin")
async def admin_menu_handler(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ У вас нет прав для использования этой команды!")
        return
    
    await message.answer(ADMIN_MENU, reply_markup=get_admin_menu_keyboard())



@router.callback_query(AdminCallback.filter(F.action == "manage_users"))
async def manage_users_handler(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\n"
        "Отправьте User ID для управления его лимитами.\n"
        "📨 Или просто перешлите сообщение от пользователя.",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminFSM.waiting_for_user_id)


@router.message(AdminFSM.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        if message.forward_from:
            user_id = message.forward_from.id
            username = message.forward_from.username
            full_name = message.forward_from.full_name

            user = await get_user_by_id(user_id)

            if not user:
                await message.answer(
                    f"❌ Пользователь с ID <code>{user_id}</code> не найден в базе.\n"
                    f"Имя: {full_name or '—'}\n"
                    f"Username: @{username or '—'}",
                    parse_mode="HTML",
                    reply_markup=get_admin_menu_keyboard()
                )
                await state.clear()
                return

            await state.update_data(target_user_id=user_id)

            registration_date = user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'
            last_reset = user.last_reset_date.strftime('%d.%m.%Y') if user.last_reset_date else 'Никогда'

            await message.answer(
                f"👤 Пользователь найден\n\n"
                f"🆔 ID: {user.user_id}\n"
                f"👤 Username: @{user.username or '—'}\n"
                f"📊 Использовано: {user.analyses_used}/{user.analyses_limit}\n"
                f"📅 Регистрация: {registration_date}\n"
                f"🔄 Последний сброс: {last_reset}\n\n"
                f"Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_user_management_keyboard()
            )
            await state.set_state(AdminFSM.managing_user)
            return

        user_id = int(message.text.strip())
        user = await get_user_by_id(user_id)

        if not user:
            await message.answer(
                f"❌ Пользователь с ID {user_id} не найден",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )
            await state.clear()
            return

        await state.update_data(target_user_id=user_id)

        registration_date = user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'
        last_reset = user.last_reset_date.strftime('%d.%m.%Y') if user.last_reset_date else 'Никогда'

        await message.answer(
            f"👤 Пользователь найден\n\n"
            f"🆔 ID: {user.user_id}\n"
            f"👤 Username: @{user.username or '—'}\n"
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
            "❌ Неверный формат. Введите числовой User ID или перешлите сообщение от пользователя.",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()



@router.callback_query(AdminFSM.managing_user, AdminCallback.filter(F.action == "set_limit"))
async def set_limit_handler(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "📊 <b>УСТАНОВКА ЛИМИТА</b>\n\n"
        "Введите новый лимит анализов для пользователя.\n"
        "Пример: <code>10</code>",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_limit)


@router.message(AdminFSM.waiting_for_limit)
async def process_new_limit(message: Message, state: FSMContext):
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
    
    elif analysis_type == "evolution":  # YANGI
        await query.message.edit_text("Выберите этап эволюции:", reply_markup=get_evolution_step_keyboard(add_mode=False))

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
    
    elif analysis_type == "evolution": 
        await query.message.edit_text("Выберите этап эволюции:", reply_markup=get_evolution_step_keyboard(add_mode=True))
        await state.set_state(AdminFSM.waiting_for_subtype)
    
    else:
        await query.message.edit_text(ENTER_PROMPT_NAME)
        await state.set_state(AdminFSM.waiting_for_prompt_name)


@router.callback_query(AdminCallback.filter(F.action == "add_select_subtype"))
async def process_add_subtype(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    subtype = callback_data.subtype
    await state.update_data(subtype=subtype, analysis_type="advanced" if subtype == "advanced" else "synthesis")
    
    await query.message.edit_text(
        "📄 <b>ЗАГРУЗКА ПРОМПТА</b>\n\n"
        "Отправьте .txt файл с промптом.\n\n"
        "ℹ️ Название будет взято из имени файла.\n"
        "Например: <code>simple_analysis.txt</code> → \"Simple Analysis\"",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_prompt_file)


@router.message(AdminFSM.waiting_for_prompt_file)
async def process_prompt_file(message: Message, state: FSMContext, bot: Bot):

    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте .txt файл")
        return
    
    if message.document.mime_type != 'text/plain':
        await message.answer("❌ Только .txt файл (text/plain)")
        return
    
    file_name = message.document.file_name
    prompt_name = file_name.replace('.txt', '').replace('_', ' ').title()

    file_io = io.BytesIO()
    try:
        await bot.download(message.document, destination=file_io)
        file_io.seek(0)
        prompt_text = file_io.read().decode('utf-8').strip()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        return
    finally:
        file_io.close()
    
    if not prompt_text:
        await message.answer("❌ Текст пустой")
        return
    
    data = await state.get_data()
    analysis_type = data.get('analysis_type', 'simple')
    category = data.get('category', 'my')

    await create_prompt(prompt_name, prompt_text, analysis_type, category)
    
    await message.answer(
        f"✅ <b>ПРОМПТ ДОБАВЛЕН</b>\n\n"
        f"📄 Название: <b>{prompt_name}</b>\n"
        f"📁 Файл: <code>{file_name}</code>\n"
        f"🎯 Тип: {analysis_type}\n"
        f"📂 Категория: {category}\n"
        f"📏 Длина: {len(prompt_text)} символов",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
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



@router.callback_query(AdminCallback.filter(F.action == "manage_samples"))
async def manage_samples_handler(query: CallbackQuery):
    try:
        reports = await SampleReportsService.get_all_sample_reports(active_only=False)
        
        if not reports:
            await query.message.edit_text(
                "📄 <b>ДЕМО ОТЧЕТЫ</b>\n\n"
                "Пока нет добавленных демо отчетов.\n"
                "Добавьте первый отчет!",
                parse_mode="HTML",
                reply_markup=get_sample_reports_keyboard([])
            )
            return
        
        regular_count = sum(1 for r in reports if r.get('video_type') == 'regular' and r['is_active'])
        shorts_count = sum(1 for r in reports if r.get('video_type') == 'shorts' and r['is_active'])
        
        text = "📄 <b>ДЕМО ОТЧЕТЫ</b>\n\n"
        text += f"📊 Всего: <code>{len(reports)}</code>\n"
        text += f"🎬 Обычные: <code>{regular_count}</code>\n"
        text += f"⚡ Shorts: <code>{shorts_count}</code>\n\n"
        
        for idx, report in enumerate(reports[:10], 1):
            status = "✅" if report['is_active'] else "❌"
            video_type_emoji = "⚡" if report.get('video_type') == 'shorts' else "🎬"
            name_short = report['report_name'][:25]
            text += f"{idx}. {status} {video_type_emoji} <b>{name_short}</b>\n"
        
        if len(reports) > 10:
            text += f"\n... и еще {len(reports) - 10} отчетов"
        
        await query.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_sample_reports_keyboard(reports[:10])
        )
    
    except Exception as e:
        await query.message.edit_text(
            f"❌ Ошибка загрузки: {str(e)}",
            reply_markup=get_back_keyboard()
        )

@router.message(AdminFSM.waiting_for_sample_url)
async def process_sample_url(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, введите URL.")
        return
    
    sample_url = message.text.strip()
    await state.update_data(sample_url=sample_url)
    
    data = await state.get_data()
    sample_name = data.get('sample_name')
    
    await message.answer(
        f"✅ URL: <code>{sample_url}</code>\n\n"
        f"Шаг 3/3: Отправьте PDF файл анализа\n\n"
        f"📎 Прикрепите PDF документ с готовым анализом.\n\n"
        f"<i>PDF будет сохранен и отправлен пользователям на бесплатном тарифе.</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_sample_data)


@router.message(AdminFSM.waiting_for_sample_data)
async def process_sample_data(message: Message, state: FSMContext, bot: Bot):
    
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте PDF файл.")
        return
    
    if message.document.mime_type != 'application/pdf':
        await message.answer("❌ Файл должен быть в формате PDF.")
        return
    
    try:
        data = await state.get_data()
        sample_name = data.get('sample_name')
        sample_url = data.get('sample_url')
        
        video_id = extract_video_id(sample_url)

        demo_dir = Path("reports/demo")
        demo_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"demo_{video_id}_{timestamp}.pdf"
        pdf_path = demo_dir / pdf_filename
        
        progress_msg = await message.answer("⏳ Сохранение PDF файла...")
        
        await bot.download(message.document, destination=str(pdf_path))
        
        analysis_data = {
            "pdf_path": str(pdf_path),
            "video_id": video_id,
            "file_size": message.document.file_size,
            "uploaded_at": datetime.now().isoformat()
        }
        
        report_id = await SampleReportsService.add_sample_report(
            report_name=sample_name,
            video_url=sample_url,
            analysis_data=analysis_data
        )
        
        await progress_msg.delete()
        
        await message.answer(
            f"✅ <b>ДЕМО ОТЧЕТ УСПЕШНО ДОБАВЛЕН!</b>\n\n"
            f"🆔 ID: <code>{report_id}</code>\n"
            f"📝 Название: <b>{sample_name}</b>\n"
            f"🔗 URL: <code>{sample_url}</code>\n"
            f"📄 PDF: <code>{pdf_filename}</code>\n"
            f"💾 Размер: <code>{message.document.file_size / 1024:.1f} KB</code>\n"
            f"📊 Статус: Активен\n\n"
            f"Этот PDF будет отправляться пользователям на бесплатном тарифе.",
            parse_mode="HTML",
            reply_markup=get_admin_menu_keyboard()
        )
        
        await state.clear()
    
    except Exception as e:
        await message.answer(
            f"❌ Ошибка сохранения: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()


@router.callback_query(AdminCallback.filter(F.action == "toggle_sample"))
async def toggle_sample_handler(query: CallbackQuery, callback_data: AdminCallback):
    try:
        report_id = callback_data.sample_id
        
        report = await SampleReportsService.get_sample_report_by_id(report_id)
        
        if not report:
            await query.answer("❌ Отчет не найден", show_alert=True)
            return
        
        if report['is_active']:
            await SampleReportsService.deactivate_sample_report(report_id)
            status_text = "деактивирован"
        else:
            await SampleReportsService.activate_sample_report(report_id)
            status_text = "активирован"
        
        await query.answer(f"✅ Отчет {status_text}", show_alert=True)

        await manage_samples_handler(query)
    
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "view_sample"))
async def view_sample_handler(query: CallbackQuery, callback_data: AdminCallback):
    try:
        report_id = callback_data.sample_id
        report = await SampleReportsService.get_sample_report_by_id(report_id)
        
        if not report:
            await query.answer("❌ Отчет не найден", show_alert=True)
            return
        
        analysis_data = report['analysis_data']
        pdf_path = analysis_data.get('pdf_path', 'Не указан')
        video_id = analysis_data.get('video_id', 'Неизвестно')
        file_size = analysis_data.get('file_size', 0)
        uploaded_at = analysis_data.get('uploaded_at', 'Неизвестно')
        
        pdf_exists = "✅ Существует" if os.path.exists(pdf_path) else "❌ Не найден"
        
        status = "✅ Активен" if report.get('is_active', True) else "❌ Неактивен"
        
        message_text = (
            f"📄 <b>ДЕМО ОТЧЕТ #{report_id}</b>\n\n"
            f"📝 <b>Название:</b> {report['report_name']}\n"
            f"🔗 <b>URL:</b> <code>{report['video_url']}</code>\n"
            f"🎬 <b>Video ID:</b> <code>{video_id}</code>\n"
            f"📊 <b>Статус:</b> {status}\n\n"
            f"<b>📎 PDF Файл:</b>\n"
            f"├ Путь: <code>{pdf_path}</code>\n"
            f"├ Размер: <code>{file_size / 1024:.1f} KB</code>\n"
            f"├ Загружен: <code>{uploaded_at[:10]}</code>\n"
            f"└ Статус: {pdf_exists}"
        )
        
        await query.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )
    
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "delete_sample"))
async def delete_sample_handler(query: CallbackQuery, callback_data: AdminCallback):
    try:
        report_id = callback_data.sample_id
        
        success = await SampleReportsService.deactivate_sample_report(report_id)
        
        if success:
            await query.answer("✅ Отчет удален", show_alert=True)
            await manage_samples_handler(query)
        else:
            await query.answer("❌ Не удалось удалить", show_alert=True)
    
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "download_sample"))
async def download_sample_handler(query: CallbackQuery, callback_data: AdminCallback):
    try:
        report_id = callback_data.sample_id
        report = await SampleReportsService.get_sample_report_by_id(report_id)
        
        if not report:
            await query.answer("❌ Отчет не найден", show_alert=True)
            return
        
        analysis_data = report['analysis_data']
        pdf_path = analysis_data.get('pdf_path')
        
        if not pdf_path or not os.path.exists(pdf_path):
            await query.answer("❌ PDF файл не найден", show_alert=True)
            return
        
        await query.message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📄 <b>{report['report_name']}</b>\n\n"
                    f"🆔 ID: <code>{report_id}</code>\n"
                    f"🔗 <code>{report['video_url']}</code>",
            parse_mode="HTML"
        )
        
        await query.answer("✅ PDF отправлен", show_alert=False)
    
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == "select_evolution"))
async def select_evolution_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    subtype = callback_data.subtype 
    data = await state.get_data()
    category = data.get('category', 'my')
    
    prompts = await get_prompts(category=category, analysis_type=subtype)
    message_text = f"📊 <b>ЭВОЛЮЦИЯ - {subtype.replace('evolution_', 'Этап ')}</b>\n\n"
    
    if prompts:
        message_text += "\n".join([f"ID {p.id}: {p.name}" for p in prompts])
    else:
        message_text += "Пока нет промптов для этого этапа."
    
    await query.message.edit_text(
        message_text,
        reply_markup=get_prompts_keyboard(prompts, subtype, category),
        parse_mode="HTML"
    )



@router.callback_query(AdminCallback.filter(F.action == "add_select_evolution"))
async def process_add_evolution(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext):
    subtype = callback_data.subtype
    await state.update_data(analysis_type=subtype)
    
    step_name = "Этап 1" if "step1" in subtype else "Этап 2"
    
    await query.message.edit_text(
        f"📊 <b>ЭВОЛЮЦИЯ - {step_name}</b>\n\n"
        f"Отправьте .txt файл с промптом.\n\n"
        f"ℹ️ Название будет взято из имени файла.\n"
        f"Например: <code>evolution_step1.txt</code> → \"Evolution Step1\"",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_prompt_file)


@router.callback_query(AdminCallback.filter(F.action == "manage_shorts_prompts"))
async def manage_shorts_prompts(query: CallbackQuery):
    """Shorts promptlarini boshqarish"""
    text = """
🎬 <b>ПРОМПТЫ ДЛЯ SHORTS</b>

Shorts имеет 3 масштаба:
- 🟢 Малый (&lt;300)
- 🟡 Средний (300-1000)
- 🔴 Большой (1000+)

Каждый масштаб имеет 5 уровней (501-505)
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Малый масштаб", callback_data="shorts_prompts:small")
    builder.button(text="🟡 Средний масштаб", callback_data="shorts_prompts:medium")
    builder.button(text="🔴 Большой масштаб", callback_data="shorts_prompts:large")
    builder.button(text="⬅️ Назад", callback_data=AdminCallback(action="back").pack())
    builder.adjust(1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("shorts_prompts:"))
async def shorts_prompts_scale(query: CallbackQuery, state: FSMContext):
    scale = query.data.split(":")[-1]
    
    scale_names = {
        'small': '🟢 Малый (&lt;300)',
        'medium': '🟡 Средний (300-1000)',
        'large': '🔴 Большой (1000+)'
    }
    
    text = f"""
{scale_names[scale]}

<b>Выберите уровень:</b>

501: Базовый анализ
502: Стратегическая оптимизация
503: Анализ хуков
504: Виральный потенциал
505: Контент-план
"""
    
    builder = InlineKeyboardBuilder()
    for level in range(501, 506):
        builder.button(
            text=f"📄 Уровень {level}",
            callback_data=f"upload_shorts:{scale}:{level}"
        )
    builder.button(text="⬅️ Назад", callback_data=AdminCallback(action="manage_shorts_prompts").pack())
    builder.adjust(1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("upload_shorts:"))
async def upload_shorts_prompt(query: CallbackQuery, state: FSMContext):
    parts = query.data.split(":")
    scale = parts[1]
    level = parts[2]  
    
    await state.update_data(shorts_scale=scale, shorts_level=level)
    
    await query.message.edit_text(
        f"📤 <b>ЗАГРУЗКА ПРОМПТА</b>\n\n"
        f"Масштаб: {scale}\n"
        f"Уровень: {level}\n\n"
        f"Отправьте .txt файл:",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_shorts_prompt)


@router.message(AdminFSM.waiting_for_shorts_prompt)
async def process_shorts_prompt(message: Message, state: FSMContext, bot: Bot):
    if not message.document or message.document.mime_type != 'text/plain':
        await message.answer("❌ Отправьте .txt файл")
        return
    
    data = await state.get_data()
    scale = data['shorts_scale']
    level = data['shorts_level']
    
    file_io = io.BytesIO()
    try:
        await bot.download(message.document, destination=file_io)
        file_io.seek(0)
        prompt_text = file_io.read().decode('utf-8').strip()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        return
    finally:
        file_io.close()

    prompt_name = f"Shorts {scale} - Level {level}"
    analysis_type = f"shorts_{scale}_{level}"
    
    await create_prompt(prompt_name, prompt_text, analysis_type, "shorts")
    
    await message.answer(
        f"✅ <b>ПРОМПТ ЗАГРУЖЕН</b>\n\n"
        f"📊 Масштаб: {scale}\n"
        f"🎯 Уровень: {level}\n"
        f"📏 Длина: {len(prompt_text)} символов",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()
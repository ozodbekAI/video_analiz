from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from handlers.analysis import ADMIN_IDS
from keyboards.client import get_main_menu_keyboard
from database.crud import (
    get_user,
    get_user_verified_channels_with_names,
    get_channel_analysis_history,
    get_evolution_prompts
)
from services.ai_service import analyze_comments_with_prompt
from services.youtube_service import get_video_channel_info
from services.pdf_generator import generate_pdf  # YANGI
from states.evolution import EvolutionFSM
import os
from pathlib import Path
from datetime import datetime

router = Router()


def get_channels_keyboard(channels: list):
    """Kanallar ro'yxati klaviaturasi (KANAL NOMI bilan)"""
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        channel_id = channel['channel_id']
        channel_title = channel['channel_title']
        video_count = channel['video_count']
        
        short_title = channel_title[:25] + "..." if len(channel_title) > 25 else channel_title
        
        builder.button(
            text=f"📺 {short_title} ({video_count})",
            callback_data=f"evolution:select:{channel_id}"
        )
    
    builder.adjust(1)
    builder.row(
        InlineKeyboardBuilder().button(
            text="↩️ Назад",
            callback_data=MenuCallback(action="main_menu")
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(MenuCallback.filter(F.action == "content_evolution"))
async def content_evolution_handler(query: CallbackQuery, state: FSMContext):
    """Evolutsiya kontenta - kanallarni ko'rsatish (Admin + User)"""
    user = await get_user(query.from_user.id)
    
    if not user:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Admin va user uchun verified kanallarni olish
    channels = await get_user_verified_channels_with_names(query.from_user.id)
    
    if not channels:
        await query.message.edit_text(
            "📊 <b>ЭВОЛЮЦИЯ КОНТЕНТА</b>\n\n"
            "❌ У вас пока нет проанализированных каналов.\n\n"
            "Сначала проведите хотя бы один анализ своего видео, "
            "чтобы увидеть эволюцию контента канала.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    is_admin = query.from_user.id in ADMIN_IDS
    admin_note = "\n\n👑 <i>Админ режим: доступны все каналы</i>" if is_admin else ""
    
    await query.message.edit_text(
        f"📊 <b>ЭВОЛЮЦИЯ КОНТЕНТА</b>\n\n"
        f"Выберите канал для анализа эволюции:\n\n"
        f"📺 Всего каналов: {len(channels)}{admin_note}",
        parse_mode="HTML",
        reply_markup=get_channels_keyboard(channels)
    )
    
    await state.set_state(EvolutionFSM.selecting_channel)


@router.callback_query(F.data.startswith("evolution:select:"))
async def select_channel_handler(query: CallbackQuery, state: FSMContext):
    """Kanalni tanlash va evolution analiz (Admin + User)"""
    channel_id = query.data.split(":", 2)[2]
    
    await state.update_data(selected_channel_id=channel_id)
    
    # User uchun tahlillar tarixini olish
    history = await get_channel_analysis_history(query.from_user.id, channel_id, limit=10)
    
    if not history:
        await query.message.edit_text(
            f"❌ Нет анализов для этого канала\n\n"
            f"Попробуйте другой канал.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return
    
    try:
        from services.youtube_service import get_channel_info_by_id
        channel_info = await get_channel_info_by_id(channel_id)
        channel_title = channel_info['title']
    except Exception:
        channel_title = channel_id[:30]
    
    is_admin = query.from_user.id in ADMIN_IDS
    admin_badge = "👑 " if is_admin else ""
    
    await query.message.edit_text(
        f"⏳ <b>{admin_badge}ЗАПУСК АНАЛИЗА ЭВОЛЮЦИИ</b>\n\n"
        f"📺 Канал: <b>{channel_title}</b>\n"
        f"📊 Найдено анализов: {len(history)}\n\n"
        f"🔄 Обработка этап 1...",
        parse_mode="HTML"
    )
    
    try:
        prompts = await get_evolution_prompts()
        
        if not prompts['step1'] or not prompts['step2']:
            await query.message.edit_text(
                "❌ <b>ОШИБКА</b>\n\n"
                "Промпты для эволюции не настроены.\n"
                "Обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return
        
        # Barcha tahlillarni yig'ish
        all_analyses = []
        for item in history:
            txt_path = item['txt_path']
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_analyses.append({
                        'date': item['processed_at'].strftime('%d.%m.%Y'),
                        'content': content
                    })
        
        if not all_analyses:
            await query.message.edit_text(
                "❌ Не удалось загрузить предыдущие анализы.\n"
                "Файлы могли быть удалены.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return
        
        # Barcha tahlillarni birlashtrish
        combined_text = "\n\n".join([
            f"=== АНАЛИЗ от {a['date']} ===\n{a['content']}"
            for a in all_analyses
        ])
        
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"📊 Обработано: {len(all_analyses)} анализов\n"
            f"🔄 Этап 1/2: Первичная обработка...",
            parse_mode="HTML"
        )
        
        # STEP 1: Первичная обработка
        step1_response = await analyze_comments_with_prompt(
            combined_text,
            prompts['step1'].prompt_text
        )
        
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Этап 1/2 завершен\n"
            f"🔄 Этап 2/2: Синтез и выводы...",
            parse_mode="HTML"
        )
        
        # STEP 2: Финальный синтез
        final_response = await analyze_comments_with_prompt(
            step1_response,
            prompts['step2'].prompt_text
        )
        
        # PDF va TXT yaratish
        user = await get_user(query.from_user.id)
        evolution_dir = Path(f"reports/{user.user_id}/evolution")
        evolution_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # TXT file
        txt_filename = f"evolution_{channel_id}_{timestamp}.txt"
        txt_path = evolution_dir / txt_filename
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"=== ЭВОЛЮЦИЯ КОНТЕНТА КАНАЛА ===\n\n")
            f.write(f"Канал: {channel_title}\n")
            f.write(f"Канал ID: {channel_id}\n")
            f.write(f"Анализов обработано: {len(all_analyses)}\n")
            f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            if is_admin:
                f.write(f"👑 Анализ выполнен администратором\n")
            f.write(f"\n{'='*60}\n\n")
            f.write(final_response)
        
        # PDF generation
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Анализ завершен\n"
            f"📄 Генерация PDF...",
            parse_mode="HTML"
        )
        
        fake_video_url = f"https://www.youtube.com/channel/{channel_id}"
        pdf_file = generate_pdf(
            final_response, 
            fake_video_url, 
            f"evolution_{channel_id}"
        )
        
        pdf_filename = f"evolution_{channel_id}_{timestamp}.pdf"
        pdf_path = evolution_dir / pdf_filename
        os.rename(pdf_file, str(pdf_path))
        
        # Send results
        await query.message.edit_text(
            f"✅ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ ЗАВЕРШЕН!</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"📊 Проанализировано: {len(all_analyses)} отчетов\n"
            f"⏱ Этапы: 2/2\n\n"
            f"📄 Отправка результата...",
            parse_mode="HTML"
        )
        
        await query.message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📊 <b>{admin_badge}Эволюция контента</b>\n\n"
                    f"📺 Канал: <b>{channel_title}</b>\n"
                    f"📈 Анализов: {len(all_analyses)}\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"<i>Полный отчет в формате PDF готов!</i>",
            parse_mode="HTML"
        )
        
        await query.message.answer(
            f"✅ Анализ эволюции завершен!\n\n"
            f"{'👑 Админ режим активен\n\n' if is_admin else ''}Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        
        await state.clear()
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        await query.message.edit_text(
            f"❌ <b>ОШИБКА</b>\n\n"
            f"Не удалось завершить анализ:\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
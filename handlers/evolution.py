from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from handlers.analysis import ADMIN_IDS
from keyboards.client import get_main_menu_keyboard
from database.crud import (
    create_evolution_analysis,
    get_user,
    get_balanced_evolution_analyses,
    get_channel_analysis_stats,
    get_evolution_prompts,
    update_evolution_step1,
    update_evolution_step2  
)
from services.ai_service import analyze_comments_with_prompt
from services.youtube_service import get_channel_info_by_id
from services.pdf_generator import generate_pdf
from states.evolution import EvolutionFSM
import os
import json
from pathlib import Path
from datetime import datetime
from utils.helpers import clean_html_for_telegram, safe_edit_text
from utils.texts import FEATURE_IN_DEVELOPMENT

router = Router()


def get_channels_keyboard(channels: list):
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        channel_id = channel['channel_id']
        channel_title = channel['channel_title']
        video_count = channel['video_count']
        
        short_title = channel_title[:25] + "..." if len(channel_title) > 25 else channel_title
        
        status_icon = "✅" if channel.get('qualified', False) else "⚠️"
        
        builder.button(
            text=f"{status_icon} {short_title} ({video_count})",
            callback_data=f"evolution:select:{channel_id}"
        )
    
    builder.adjust(1)
    builder.row(
        InlineKeyboardBuilder().button(
            text="↩️ Назад",
            callback_data=MenuCallback(action="main_menu").pack()
        ).as_markup().inline_keyboard[0][0]
    )
    
    return builder.as_markup()


@router.callback_query(MenuCallback.filter(F.action == "content_evolution"))
async def content_evolution_handler(query: CallbackQuery, state: FSMContext):
    """Обработчик эволюции контента с проверкой требований"""
    user = await get_user(query.from_user.id)
    
    if not user:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    from database.crud import get_user_verified_channels_with_names
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
    
    qualified_channels = []
    for channel in channels:
        stats = await get_channel_analysis_stats(query.from_user.id, channel['channel_id'])
        channel['stats'] = stats
        channel['qualified'] = stats['advanced'] >= 5
        if channel['qualified']:
            qualified_channels.append(channel)
    
    is_admin = query.from_user.id in ADMIN_IDS
    admin_note = "\n\n👑 <i>Админ режим: доступны все каналы</i>" if is_admin else ""
    
    qualified_count = len(qualified_channels)
    total_count = len(channels)
    
    status_message = (
        f"📊 <b>ЭВОЛЮЦИЯ КОНТЕНТА</b>\n\n"
        f"Выберите канал для анализа эволюции:\n\n"
        f"📺 Всего каналов: {total_count}\n"
        f"✅ Доступно для анализа: {qualified_count}\n"
        f"{admin_note}\n\n"
        f"<i>Требуется минимум 5 углубленных анализов для качественного результата.</i>"
    )
    
    await query.message.edit_text(
        status_message,
        parse_mode="HTML",
        reply_markup=get_channels_keyboard(channels)
    )
    
    await state.set_state(EvolutionFSM.selecting_channel)


def extract_machine_data_from_file(txt_path: str) -> dict:
    """
    TXT fayldan machine_data JSON ni extract qiladi
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JSON bloklarni qidirish
        if '```json' in content:
            # Markdown JSON bloki
            json_start = content.find('```json') + 7
            json_end = content.find('```', json_start)
            if json_end != -1:
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
        
        # To'g'ridan-to'g'ri JSON qidiramiz
        if content.strip().startswith('{'):
            return json.loads(content)
        
        # Agar JSON topilmasa, bo'sh dict qaytaramiz
        return {}
        
    except Exception as e:
        print(f"⚠️ Machine data extract qilishda xato: {e}")
        return {}


@router.callback_query(F.data.startswith("evolution:select:"))
async def select_channel_handler(query: CallbackQuery, state: FSMContext):
    channel_id = query.data.split(":", 2)[2]
    await state.update_data(selected_channel_id=channel_id)
    
    is_admin = query.from_user.id in ADMIN_IDS
    admin_badge = "👑 " if is_admin else ""

    try:
        channel_info = await get_channel_info_by_id(channel_id)
        channel_title = channel_info['title']
    except Exception:
        channel_title = channel_id[:30] + "..."
    
    # 🔥 YANGI: balanced_analyses dan AI responses ham olamiz
    balanced_analyses = await get_balanced_evolution_analyses(
        user_id=query.from_user.id,
        channel_id=channel_id,
        min_advanced=5,
        total_limit=10
    )

    if not balanced_analyses:
        stats = await get_channel_analysis_stats(query.from_user.id, channel_id)
        
        error_message = (
            f"❌ <b>НЕДОСТАТОЧНО ДАННЫХ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"📊 Статистика:\n"
            f"  • Всего анализов: {stats['total']}\n"
            f"  • Углубленных: {stats['advanced']}\n"
            f"  • Простых: {stats['simple']}\n\n"
            f"<b>Требования:</b>\n"
            f"✅ Минимум <b>5 углубленных анализов</b>\n\n"
            f"<i>Проведите еще {max(0, 5 - stats['advanced'])} углубленный(х) анализ(ов)</i>"
        )
        
        await query.message.edit_text(
            error_message,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return

    advanced_count = sum(1 for video, ai in balanced_analyses if ai.analysis_type == 'advanced')
    simple_count = len(balanced_analyses) - advanced_count
    
    dates = [video.first_comment_date for video, ai in balanced_analyses if video.first_comment_date]
    if dates:
        earliest_date = min(dates).strftime('%d.%m.%Y')
        latest_date = max(dates).strftime('%d.%m.%Y')
        date_range = f"\n📅 Период: {earliest_date} — {latest_date}"
    else:
        date_range = ""
    
    await query.message.edit_text(
        f"⏳ <b>{admin_badge}ЗАПУСК АНАЛИЗА ЭВОЛЮЦИИ</b>\n\n"
        f"📺 Канал: <b>{channel_title}</b>\n"
        f"📊 Анализов: {len(balanced_analyses)} ({advanced_count} углубл. + {simple_count} прост.){date_range}\n\n"
        f"🔄 Этап 0/2: Подготовка данных...",
        parse_mode="HTML"
    )
    
    try:
        prompts = await get_evolution_prompts()
        
        if not prompts['step1'] or not prompts['step2']:
            await query.message.edit_text(
                "❌ <b>ОШИБКА КОНФИГУРАЦИИ</b>\n\n"
                "Промпты для эволюции не настроены в системе.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        all_analyses = []
        video_ids_used = []
        
        for idx, (video, ai_response) in enumerate(balanced_analyses, 1):
            video_id = video.id
            video_url = video.video_url
            analysis_type = ai_response.analysis_type
            processed_date = video.processed_at.strftime('%d.%m.%Y')
            
            machine_data = None
            if ai_response.machine_data:
                # Agar DBda JSON saqlangan bo'lsa
                if isinstance(ai_response.machine_data, dict):
                    machine_data = ai_response.machine_data
                elif isinstance(ai_response.machine_data, str):
                    try:
                        machine_data = json.loads(ai_response.machine_data)
                    except:
                        pass
            
            # Fallback: TXT fayldan o'qish (eski versiya uchun)
            if not machine_data and ai_response.txt_file_path and os.path.exists(ai_response.txt_file_path):
                machine_data = extract_machine_data_from_file(ai_response.txt_file_path)
            
            # Agar machine_data topilmasa, response_text ishlatamiz
            if machine_data:
                content = json.dumps(machine_data, ensure_ascii=False, indent=2)
                data_source = "JSON"
            elif ai_response.response_text:
                content = ai_response.response_text
                data_source = "TEXT"
            else:
                print(f"⚠️ Video {video_id} uchun ma'lumot topilmadi")
                continue
            
            all_analyses.append({
                'number': idx,
                'date': processed_date,
                'video_url': video_url,
                'type': analysis_type,
                'content': content,
                'data_source': data_source
            })
            video_ids_used.append(video_id)
        
        if len(all_analyses) < 5:
            await query.message.edit_text(
                f"❌ <b>ОШИБКА ЗАГРУЗКИ</b>\n\n"
                f"Удалось загрузить только {len(all_analyses)} анализов.\n"
                f"Требуется минимум 5.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        user = await get_user(query.from_user.id)
        
        evolution = await create_evolution_analysis(
            user_id=user.user_id,
            channel_id=channel_id,
            channel_title=channel_title,
            videos_analyzed=len(all_analyses),
            video_ids_used=video_ids_used
        )
        
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Загружено: {len(all_analyses)} анализов\n"
            f"🔄 Этап 1/2: Объединение данных...",
            parse_mode="HTML"
        )
        
        # 🔥 YANGI: combined_text ni yaratishda data_source ni ko'rsatamiz
        combined_text = ""
        for analysis in all_analyses:
            type_label = "УГЛУБЛЕННЫЙ" if analysis['type'] == 'advanced' else "ПРОСТОЙ"
            data_label = f" [{analysis['data_source']}]"
            
            combined_text += f"""
╔═══════════════════════════════════════════════════════════════
║ АНАЛИЗ #{analysis['number']} ({type_label}{data_label}) от {analysis['date']}
║ Видео: {analysis['video_url']}
╚═══════════════════════════════════════════════════════════════

{analysis['content']}

{'=' * 80}

"""
        
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Обработано: {len(all_analyses)} анализов\n"
            f"🔄 Этап 1/2: AI обработка...\n\n"
            f"<i>Это может занять 1-2 минуты</i>",
            parse_mode="HTML"
        )
        
        step1_response = await analyze_comments_with_prompt(
            combined_text,
            prompts['step1'].prompt_text
        )
        
        await update_evolution_step1(evolution.id, step1_response)

        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Этап 1/2 завершен\n"
            f"🔄 Этап 2/2: Финальный синтез...\n\n"
            f"<i>Это может занять 1-2 минуты</i>",
            parse_mode="HTML"
        )
        
        final_response = await analyze_comments_with_prompt(
            step1_response,
            prompts['step2'].prompt_text
        )
        
        await query.message.edit_text(
            f"⏳ <b>{admin_badge}АНАЛИЗ ЭВОЛЮЦИИ</b>\n\n"
            f"📺 Канал: <b>{channel_title}</b>\n"
            f"✅ Анализ завершен\n"
            f"📄 Генерация отчета...",
            parse_mode="HTML"
        )
        
        evolution_dir = Path(f"reports/{user.user_id}/evolution")
        evolution_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        txt_filename = f"evolution_{channel_id}_{timestamp}.txt"
        txt_path = evolution_dir / txt_filename
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ЭВОЛЮЦИЯ КОНТЕНТА КАНАЛА\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Канал: {channel_title}\n")
            f.write(f"Канал ID: {channel_id}\n")
            f.write(f"Анализов: {len(all_analyses)} ({advanced_count} углубл. + {simple_count} прост.)\n")
            if date_range:
                f.write(f"Период: {earliest_date} — {latest_date}\n")
            f.write(f"Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write(final_response)

        fake_video_url = f"https://www.youtube.com/channel/{channel_id}"
        pdf_file = generate_pdf(
            final_response, 
            fake_video_url, 
            f"evolution_{channel_id}"
        )
        
        pdf_filename = f"evolution_{channel_id}_{timestamp}.pdf"
        pdf_path = evolution_dir / pdf_filename
        os.rename(pdf_file, str(pdf_path))

        analysis_period = f"{earliest_date} — {latest_date}" if dates else "неизвестный период"
        await update_evolution_step2(
            evolution.id,
            final_response,
            pdf_path=str(pdf_path),
            txt_path=str(txt_path),
            analysis_period=analysis_period
        )

        safe_summary = clean_html_for_telegram(
            f"✅ <b>{admin_badge}АНАЛИЗ ЗАВЕРШЕН!</b>\n\n"
            f"📺 {channel_title}\n"
            f"📊 Анализов: {len(all_analyses)} ({advanced_count} углубл. + {simple_count} прост.)\n"
            f"📅 {analysis_period}"
        )
        
        await query.message.edit_text(safe_summary, parse_mode="HTML")
        
        await query.message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📊 <b>{admin_badge}Эволюция контента</b>\n\n"
                    f"📺 {channel_title}\n"
                    f"📈 Анализов: {len(all_analyses)}\n"
                    f"📅 {analysis_period}\n"
                    f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
        
        await query.message.answer(
            "✅ <b>Готово!</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
        await state.clear()
    
    except Exception as e:
        import traceback
        print(f"❌ EVOLUTION ERROR:\n{traceback.format_exc()}")
        
        safe_error = clean_html_for_telegram(
            f"❌ <b>ОШИБКА</b>\n\n{str(e)[:200]}"
        )
        
        await query.message.edit_text(
            safe_error,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

async def universal_analysis_handler(
    query: CallbackQuery,
    state: FSMContext,
    analysis_type: str
):
    """
    Universal handler:
    audience_map
    content_prediction
    channel_diagnostics
    content_ideas
    viral_potential
    iterative_ideas
    """
    await state.clear()

    await safe_edit_text(
        query,
        FEATURE_IN_DEVELOPMENT,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
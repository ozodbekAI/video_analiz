from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback
from services.advanced_analysis_handler import run_advanced_analysis_with_validation
from states.analysis import AnalysisFSM
from keyboards.client import (
    get_analysis_type_keyboard, 
    get_back_to_menu_keyboard, 
    get_main_menu_keyboard,
    get_after_analysis_keyboard
)
from services.youtube_service import (
    extract_video_id,
    format_timestamps_for_analysis, 
    get_video_comments, 
    get_video_comments_count,
    get_video_timestamps, 
    save_comments_to_file, 
    get_comments_file_path,
    get_video_channel_info,
    get_video_comments_with_metrics
)
from services.ai_service import analyze_comments_with_prompt, save_ai_interaction
from services.pdf_generator import generate_pdf
from services.verifiaction_service import VerificationService
from services.sample_report_service import SampleReportsService
from database.crud import get_user, update_user_analyses, create_video, get_prompts, create_ai_response
from utils.texts import ENTER_VIDEO_URL, INVALID_URL, LIMIT_EXCEEDED, ANALYSIS_STARTED, ANALYSIS_DONE
from utils.progress import ProgressTracker
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from config import config

router = Router()

user_analysis_locks = {}
pending_verification_channels = {}
ADMIN_IDS = config.ADMIN_IDS


def get_owner_check_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, я владелец канала", callback_data="check_owner")
    builder.button(text="🚫 Нет, просто смотрю", callback_data=MenuCallback(action="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(MenuCallback.filter(F.action == "analysis_my_video"))
async def analysis_my_video_handler(query: CallbackQuery, state: FSMContext):
    await state.clear() 
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="my")
    
    await query.message.edit_text("Выберите тип анализа:", reply_markup=get_analysis_type_keyboard("my"))


@router.callback_query(MenuCallback.filter(F.action == "analysis_competitor"))
async def analysis_competitor_handler(query: CallbackQuery, state: FSMContext):
    user = await get_user(query.from_user.id)
    
    if user.tariff_plan not in ['pro', 'business', 'enterprise'] and query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Эта функция доступна только для пользователей Premium тарифа.", show_alert=True)
        return

    await state.clear()  
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="competitor")
    
    await query.message.edit_text("Выберите тип анализа:", reply_markup=get_analysis_type_keyboard("competitor"))


@router.callback_query(AnalysisFSM.choose_type, AnalysisCallback.filter(F.type == "simple"))
async def choose_simple_analysis(query: CallbackQuery, callback_data: AnalysisCallback, state: FSMContext):
    user = await get_user(query.from_user.id)
    
    if user.analyses_used >= user.analyses_limit and query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Достигнут лимит анализов.", show_alert=True)
        return

    data = await state.get_data()
    category = data.get('analysis_category')
    
    await state.set_state(AnalysisFSM.waiting_for_url)
    await state.update_data(
        analysis_category=category,
        analysis_type="simple"
    )
    
    await query.message.edit_text(ENTER_VIDEO_URL, reply_markup=get_back_to_menu_keyboard())


@router.callback_query(AnalysisFSM.choose_type, AnalysisCallback.filter(F.type == "advanced"))
async def choose_advanced_analysis(query: CallbackQuery, callback_data: AnalysisCallback, state: FSMContext):
    user = await get_user(query.from_user.id)
    
    if user.tariff_plan not in ['pro', 'business', 'enterprise'] and query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Эта функция доступна только для пользователей Premium тарифа.", show_alert=True)
        return
        
    data = await state.get_data()
    category = data.get('analysis_category')
    
    await state.set_state(AnalysisFSM.waiting_for_url)
    await state.update_data(
        analysis_category=category,
        analysis_type="advanced"
    )
    
    await query.message.edit_text(ENTER_VIDEO_URL, reply_markup=get_back_to_menu_keyboard())


@router.callback_query(AnalysisFSM.choose_type, MenuCallback.filter(F.action == "main_menu"))
async def back_from_analysis_type(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("Главное меню", reply_markup=get_main_menu_keyboard())
    await state.clear()


async def update_progress_message(message: Message, text: str, emoji: str = "⏳"):
    try:
        progress_bar = f"{emoji} {text}"
        await message.edit_text(progress_bar)
    except Exception:
        await message.answer(f"{emoji} {text}")


async def send_sample_report_and_ask(message: Message, user_id: int, video_type: str = 'regular'):
    try:
        sample_report = await SampleReportsService.get_random_sample_report(video_type)
        
        if not sample_report:
            await message.answer(
                f"❌ Демо отчеты ({video_type}) недоступны.\n\n"
                f"Администратор пока не загрузил примеры.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        video_type_ru = "Shorts" if video_type == 'shorts' else "обычного видео"
        
        await message.answer(
            f"📊 <b>ДЕМО АНАЛИЗ</b>\n\n"
            f"На бесплатном тарифе мы показываем демо-версию анализа {video_type_ru}.\n\n"
            f"<i>Это образец отчета для ознакомления.</i>\n\n"
            f"Чтобы получить реальный анализ, подтвердите владение каналом.",
            parse_mode="HTML"
        )
        
        analysis_data = sample_report['analysis_data'] 
        pdf_path = analysis_data.get('pdf_path')
        
        if not pdf_path or not os.path.exists(pdf_path):
            await message.answer(
                "❌ PDF файл не найден в системе.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        progress_msg = await message.answer("📄 Загрузка демо-отчета...")
        
        video_type_emoji = "⚡" if video_type == 'shorts' else "🎬"
        
        await message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📊 <b>ДЕМО Анализ готов!</b>\n\n"
                    f"{video_type_emoji} Тип: <b>{video_type_ru.capitalize()}</b>\n"
                    f"📝 Название: <i>{sample_report['report_name']}</i>\n\n"
                    f"<i>Это образец анализа для ознакомления.</i>",
            parse_mode="HTML"
        )
        
        await progress_msg.delete()

        await message.answer(
            "❓ <b>Вы владелец канала?</b>\n\n"
            "Подтвердите канал для получения реальных анализов!",
            reply_markup=get_owner_check_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка загрузки демо: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )


async def check_video_ownership(user_id: int, video_url: str, is_admin: bool = False) -> tuple[bool, str, Optional[str]]:
    try:
        from services.youtube_service import get_video_channel_info
        
        channel_info = await get_video_channel_info(video_url)
        
        if not channel_info:
            return False, "Не удалось получить информацию о канале", None
        
        video_channel_url = channel_info['channel_url']
        video_channel_id = channel_info['channel_id']
        video_channel_title = channel_info['channel_title']
        
        if is_admin:
            return True, f"👑 Админ доступ: {video_channel_title}", None
    
        verification_status = await VerificationService.get_user_verification_status(user_id)
        
        if not verification_status['is_verified']:
            return False, f"Канал не подтвержден.\n\nВидео из: {video_channel_title}", video_channel_url
        
        user_channel_id = verification_status['channel_id']
        
        if video_channel_id in user_channel_id or user_channel_id in video_channel_url:
            return True, f"Вы владелец: {video_channel_title}", None
        else:
            return False, f"Видео с другого канала: {video_channel_title}", video_channel_url
    
    except Exception as e:
        return False, f"Ошибка: {str(e)}", None


async def run_analysis_task(user_id: int, message: Message, url: str, category: str, analysis_type: str):
    progress_msg = None
    try:
        
        user = await get_user(user_id)
        
        if user is None:
            # Если get_user возвращает None, создаём пользователя
            from database.crud import ensure_user_exists
            user = await ensure_user_exists(user_id)
        is_admin = user_id in ADMIN_IDS
        
        from services.youtube_service import is_shorts_video
        is_shorts = await is_shorts_video(url)
        video_type = 'shorts' if is_shorts else 'regular'
        
        is_owner, ownership_msg, channel_url_to_verify = await check_video_ownership(user_id, url, is_admin=is_admin)
        
        if not is_admin:
            if not is_owner:
                await send_sample_report_and_ask(message, user_id, video_type)
                return
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            
            pending_verification_channels[user_id] = channel_url_to_verify
            
            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ Подтвердить канал", 
                callback_data="verify:start_from_analysis"
            )
            builder.button(text="🚫 Отмена", callback_data="menu:main_menu")
            builder.adjust(1)
            
            await message.answer(
                f"🔒 <b>ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ</b>\n\n"
                f"{ownership_msg}\n\n"
                f"Подтвердите владение каналом для анализа.\n\n"
                f"<i>После подтверждения анализ продолжится автоматически.</i>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            return
        
        if not is_admin:
            if user.analyses_used >= user.analyses_limit:
                await message.answer(
                    f"❌ Достигнут лимит анализов.\n\n"
                    f"📊 Использовано: {user.analyses_used}/{user.analyses_limit}",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return
        
        progress_msg = await message.answer("⏳ Загрузка комментариев...")
        
        video_id = extract_video_id(url)
        from services.youtube_service import get_video_comments_with_metrics
        
        comments_result = get_video_comments_with_metrics(video_id)
        comments_data = comments_result['comments']
        engagement_metrics = comments_result['metrics']
        engagement_phases = comments_result['engagement_phases']
        top_authors = comments_result['top_authors']
        video_meta_full = comments_result['metadata']
        
        comments_file = get_comments_file_path(video_id)
        comments_len = len(comments_data)

        if comments_len >= 2000 and analysis_type == "advanced":
            if user.tariff_plan not in ['pro', 'business', 'enterprise'] and not is_admin:
                raise ValueError("❌ Превышен лимит в 2000 комментариев для анализа.")

        await update_progress_message(
            progress_msg, 
            f"✅ Загружено {comments_len} комментариев\n🔄 Получение timestamps..."
        )
        
        timestamps_info = await get_video_timestamps(url)
        timestamps_text = format_timestamps_for_analysis(timestamps_info['timestamps'])
        
        save_comments_to_file(comments_data, comments_file)
        
        if timestamps_info['has_timestamps']:
            with open(comments_file, "a", encoding="utf-8") as f:
                f.write(timestamps_text)
        
        await update_progress_message(
            progress_msg, 
            f"✅ Загружено {comments_len} комментариев\n✅ Timestamps: {timestamps_info['timestamps_count']}\n🔄 Сохранение в базу данных..."
        )
        
        db_video_id = await create_video(
            user.id, 
            url, 
            f"Comments: {comments_file}"
        )
        
        try:
            channel_info = await get_video_channel_info(url)
            channel_id = channel_info.get('channel_id') if channel_info else None
            channel_title = channel_info.get('channel_title') if channel_info else None
        except Exception:
            channel_id = None
            channel_title = None

        from database.crud import update_video_channel_id
        if channel_id:
            await update_video_channel_id(db_video_id, channel_id)
        
        if is_admin and channel_id:
            from database.crud import create_admin_verified_channel
            await create_admin_verified_channel(
                user_id=user.id,
                channel_id=channel_id,
                channel_title=channel_title or channel_id[:30]
            )
        
        with open(comments_file, "r", encoding="utf-8") as f:
            full_context = f.read()
        
        ai_response_id_for_files = None

        if analysis_type == "simple":
            await update_progress_message(
                progress_msg,
                "🤖 Анализ комментариев через AI...\n⏱ Это может занять 30-60 секунд"
            )
            
            simple_prompts = await get_prompts(category=category, analysis_type="simple")
            if not simple_prompts:
                raise ValueError("Нет промпта для простого анализа")
            
            prompt_text = simple_prompts[0].prompt_text
            request_context = full_context
            
            ai_response = await analyze_comments_with_prompt(full_context, prompt_text)

            ai_logs = save_ai_interaction(
                user_id=user.user_id,
                video_id=video_id,
                stage="simple",
                request_text=request_context,
                response_text=ai_response
            )
            
            ai_response_id_for_files = await create_ai_response(
                user.id, 
                db_video_id, 
                0, 
                "simple", 
                ai_response
            )
            
            final_ai_response = ai_response

            try:
                await message.answer(
                    f"📊 <b>AI ЛОГИ - ПРОСТОЙ АНАЛИЗ</b>\n\n"
                    f"📹 Video ID: <code>{video_id}</code>\n"
                    f"📥 Request: <code>{ai_logs['request_size']} KB</code>\n"
                    f"📤 Response: <code>{ai_logs['response_size']} KB</code>\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"<i>Отправка файлов...</i>",
                    parse_mode="HTML"
                )

                await message.answer_document(
                    FSInputFile(ai_logs['request_path']),
                    caption=f"📥 <b>AI REQUEST</b>\n\n"
                            f"🎯 Simple Analysis\n"
                            f"📏 {ai_logs['request_size']} KB",
                    parse_mode="HTML"
                )
                
                await message.answer_document(
                    FSInputFile(ai_logs['response_path']),
                    caption=f"📤 <b>AI RESPONSE</b>\n\n"
                            f"🎯 Simple Analysis\n"
                            f"📏 {ai_logs['response_size']} KB",
                    parse_mode="HTML"
                )
                
            except Exception as e:
                print(f"❌ AI logs yuborishda xatolik: {e}")
        
        elif analysis_type == "advanced":
            advanced_prompts = await get_prompts(category=category, analysis_type="advanced")
            final_ai_response, all_partial_logs, machine_data_json, final_ai_response_id = await run_advanced_analysis_with_validation(
                user_id=user.user_id,
                video_id=video_id,
                db_video_id=db_video_id,
                full_context=full_context,
                category=category,
                video_meta_full=video_meta_full,
                progress_msg=progress_msg,
                message=message,
                update_progress_message=update_progress_message
            )

            ai_response_id_for_files = final_ai_response_id or None
            
            # Only AI log files (filter out structured validation entries)
            ai_logs_only = [
                l for l in all_partial_logs
                if isinstance(l, dict) and l.get('request_path') and l.get('response_path')
            ]
            
            # ===== AI LOGLARNI YUBORISH =====
            try:
                await message.answer(
                    f"📊 <b>AI ЛОГИ - УГЛУБЛЕННЫЙ АНАЛИЗ</b>\n\n"
                    f"📹 Video ID: <code>{video_id}</code>\n"
                    f"🔢 Этапов: {len(ai_logs_only)}\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"<i>Отправка всех файлов...</i>",
                    parse_mode="HTML"
                )
                
                # Faqat AI loglarni yuborish
                for idx, log in enumerate(ai_logs_only):
                    stage_name = "СИНТЕЗ" if idx == len(ai_logs_only) - 1 else f"ЭТАП {idx+1}"
                    
                    await message.answer_document(
                        FSInputFile(log['request_path']),
                        caption=f"📥 <b>{stage_name} - REQUEST</b>\n\n"
                                f"📏 {log['request_size']} KB",
                        parse_mode="HTML"
                    )
                    
                    await message.answer_document(
                        FSInputFile(log['response_path']),
                        caption=f"📤 <b>{stage_name} - RESPONSE</b>\n\n"
                                f"📏 {log['response_size']} KB",
                        parse_mode="HTML"
                    )
                
            except Exception as e:
                print(f"❌ Ошибка отправки логов: {e}")
            
            # ===== MACHINE DATA FILE (optional, for debugging / admin) =====
            if machine_data_json and final_ai_response_id:
                try:
                    reports_dir = Path(f"reports/{user.user_id}")
                    reports_dir.mkdir(parents=True, exist_ok=True)

                    machine_json_path = reports_dir / f"{video_id}_machine_{final_ai_response_id}.json"
                    with open(machine_json_path, "w", encoding="utf-8") as f:
                        f.write(machine_data_json)
                except Exception as e:
                    print(f"⚠️ Machine data file saqlashda xato: {e}")

        else:
            raise ValueError("Неизвестный тип анализа")

        await update_progress_message(
            progress_msg,
            "📄 Генерация PDF отчета..."
        )

        pdf_file = generate_pdf(final_ai_response, url, video_id)
        
        reports_dir = Path(f"reports/{user.user_id}")
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_suffix = ai_response_id_for_files or int(datetime.now().timestamp())
        saved_pdf_path = reports_dir / f"{video_id}_{analysis_type}_{file_suffix}.pdf"
        os.rename(pdf_file, str(saved_pdf_path))
        pdf_file = str(saved_pdf_path)

        txt_file_path = reports_dir / f"{video_id}_{analysis_type}_{file_suffix}.txt"
        with open(txt_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(f"=== ANALIZ NATIJALARI ===\n\n")
            txt_file.write(f"Video ID: {video_id}\n")
            txt_file.write(f"Video URL: {url}\n")
            txt_file.write(f"Kanal: {channel_title or 'Unknown'}\n")
            txt_file.write(f"Kanal ID: {channel_id or 'Unknown'}\n")
            txt_file.write(f"Tahlil turi: {'Oddiy' if analysis_type == 'simple' else 'Chuqur'}\n")
            txt_file.write(f"Kommentlar soni: {comments_len}\n")
            txt_file.write(f"Timestamps soni: {timestamps_info['timestamps_count']}\n")
            txt_file.write(f"Sana: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            
            # 🆕 ENGAGEMENT METRICS
            txt_file.write(f"\n=== ENGAGEMENT METRICS ===\n")
            txt_file.write(f"Total Comments: {engagement_metrics['total_comments']}\n")
            txt_file.write(f"Total Replies: {engagement_metrics['total_replies']}\n")
            txt_file.write(f"Engagement Rate: {engagement_metrics['engagement_rate']}%\n")
            txt_file.write(f"Like Ratio: {engagement_metrics['like_ratio']}%\n")
            txt_file.write(f"Comment Velocity: {engagement_metrics['comment_velocity']} comments/hour\n")
            
            # 🆕 TIME DISTRIBUTION
            txt_file.write(f"\n=== TIME DISTRIBUTION ===\n")
            for period, count in engagement_metrics['time_distribution'].items():
                txt_file.write(f"{period}: {count} comments\n")
            
            # 🆕 ENGAGEMENT PHASES
            txt_file.write(f"\n=== ENGAGEMENT PHASES ===\n")
            for phase, stats in engagement_phases.items():
                txt_file.write(f"{phase}: {stats['comments']} comments, {stats['replies']} replies\n")
            
            # 🆕 TOP AUTHORS
            txt_file.write(f"\n=== TOP 10 AUTHORS ===\n")
            for idx, author in enumerate(top_authors[:10], 1):
                txt_file.write(
                    f"{idx}. {author['author']}: "
                    f"{author['comments']} comments, "
                    f"{author['replies']} replies, "
                    f"{author['total_likes']} likes\n"
                )
            
            if is_admin:
                txt_file.write(f"\nAdmin tomonidan tahlil qilindi\n")
            
            txt_file.write(f"\n{'='*50}\n\n")
            txt_file.write(final_ai_response)

        # Save file paths for this exact analysis row
        try:
            from database.crud import update_ai_response_files_by_id, register_advanced_analysis_to_set

            if ai_response_id_for_files:
                await update_ai_response_files_by_id(
                    int(ai_response_id_for_files),
                    txt_path=str(txt_file_path),
                    pdf_path=str(saved_pdf_path),
                )

                # TZ-2: advanced analyses are grouped into sets for later evaluation
                if analysis_type == "advanced":
                    await register_advanced_analysis_to_set(
                        user_identifier=user.user_id,
                        youtube_video_id=video_id,
                        db_video_id=db_video_id,
                        ai_response_id=int(ai_response_id_for_files),
                    )
        except Exception as e:
            print(f"⚠️ AIResponse file path / set registration error: {e}")

        if progress_msg:
            await progress_msg.delete()
            progress_msg = None

        await message.answer_document(
            FSInputFile(pdf_file),
            caption=f"📊 <b>Анализ готов!</b>\n\n"
                    f"📹 Видео: <code>{video_id}</code>\n"
                    f"📺 Канал: {channel_title or 'Unknown'}\n"
                    f"📝 Комментариев: {comments_len}\n"
                    f"⏱ Timestamps: {timestamps_info['timestamps_count']}\n"
                    f"🎯 Тип: {'Простой' if analysis_type == 'simple' else 'Углубленный'}\n"
                    f"{'👑 Админ анализ' if is_admin else ''}\n",
            parse_mode="HTML",
        )

        if not is_admin:
            remaining = user.analyses_limit - (user.analyses_used + 1)
            await message.answer(
                f"✅ Анализ завершен!\n\n"
                f"📊 Осталось анализов: {remaining}/{user.analyses_limit}\n\n"
                f"Выберите действие:",
                reply_markup=get_after_analysis_keyboard()
            )
        else:
            await message.answer(
                f"✅ Анализ завершен!\n\n"
                f"👑 Вы администратор - безлимитный доступ\n"
                f"✅ Канал добавлен для эволюции\n\n"
                f"Выберите действие:",
                reply_markup=get_after_analysis_keyboard()
            )
        if not is_admin:
            await update_user_analyses(user.id, user.analyses_used + 1)
        
    except ValueError as e:
        if progress_msg:
            await update_progress_message(progress_msg, f"❌ Ошибка: {str(e)}")
        await message.answer(
            f"❌ {str(e)}\n\nВернуться в меню:",
            reply_markup=get_main_menu_keyboard()
        )
    except FileNotFoundError as e:
        if progress_msg:
            await update_progress_message(progress_msg, "❌ Файл не найден")
        await message.answer(
            f"Файл не найден: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
    except OSError as e:
        if progress_msg:
            await update_progress_message(progress_msg, "❌ Ошибка файловой системы")
        await message.answer(
            f"Ошибка файловой операции: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        if progress_msg:
            await update_progress_message(progress_msg, "❌ Неожиданная ошибка")
        await message.answer(
            f"Ошибка: {str(e)}\n\nВернуться в меню:",
            reply_markup=get_main_menu_keyboard()
        )
        

@router.message(AnalysisFSM.waiting_for_url)
async def process_video_url(message: Message, state: FSMContext):
    url = message.text.strip()
    user_id = message.from_user.id
    
    if user_id in user_analysis_locks and not user_analysis_locks[user_id].done():
        await message.answer(
            "⏳ У вас уже идет анализ. Дождитесь завершения текущего.\n\n"
            "Вы можете продолжить использовать бот:",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    data = await state.get_data()
    category = data.get('analysis_category')
    analysis_type = data.get('analysis_type')
    
    await state.update_data(
        pending_video_url=url,
        pending_analysis_category=category,
        pending_analysis_type=analysis_type
    )
    
    task = asyncio.create_task(
        run_analysis_task(user_id, message, url, category, analysis_type)
    )
    user_analysis_locks[user_id] = task
    
    def cleanup(t):
        if user_id in user_analysis_locks:
            del user_analysis_locks[user_id]
    
    task.add_done_callback(cleanup)
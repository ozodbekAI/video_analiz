from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback
from states.analysis import AnalysisFSM
from keyboards.client import (
    get_analysis_type_keyboard, 
    get_back_to_menu_keyboard, 
    get_main_menu_keyboard,
    get_after_analysis_keyboard
)
from services.youtube_service import (
    extract_video_id, 
    get_video_comments, 
    get_video_comments_count, 
    save_comments_to_file, 
    get_comments_file_path,
    get_video_channel_info
)
from services.ai_service import analyze_comments_with_prompt
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
    
    # Проверка лимита (не для админов)
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


async def send_sample_report_and_ask(message: Message, user_id: int):
    try:
        sample_report = await SampleReportsService.get_random_sample_report()
        
        if not sample_report:
            await message.answer(
                "❌ Демо отчеты недоступны. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        await message.answer(
            f"📊 <b>ДЕМО АНАЛИЗ</b>\n\n"
            f"На бесплатном тарифе мы показываем вам демо-версию анализа, "
            f"чтобы продемонстрировать возможности YT Pulse AI.\n\n"
            f"<i>Это не анализ вашего видео, а образец отчета.</i>\n\n"
            f"Чтобы получить реальный и точный анализ, необходимо подтвердить владение каналом.",
            parse_mode="HTML"
        )
        
        analysis_data = sample_report['analysis_data'] 
        pdf_path = analysis_data.get('pdf_path')
        video_url = sample_report['video_url']
        video_id = extract_video_id(video_url)
        
        if not pdf_path or not os.path.exists(pdf_path):
            await message.answer(
                "❌ PDF файл демо отчета не найден. Пожалуйста, обратитесь к администратору.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        progress_msg = await message.answer("📄 Загрузка PDF отчета...")
        
        await message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📊 <b>ДЕМО Анализ готов!</b>\n\n"
                    f"📹 Видео: <code>{video_id}</code>\n"
                    f"🎯 Тип: Демонстрационный отчет\n\n"
                    f"<i>Это образец анализа для ознакомления с возможностями бота.</i>",
            parse_mode="HTML"
        )
        
        await progress_msg.delete()
        
        await message.answer(
            "❓ <b>Вы владелец этого или другого канала?</b>\n\n"
            "Если да, подтвердите свой канал и получите доступ к реальным анализам!",
            reply_markup=get_owner_check_keyboard(),
            parse_mode="HTML"
        )
        
    except json.JSONDecodeError:
        await message.answer(
            "❌ Ошибка при обработке демо отчета. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}\n\nВернуться в меню:",
            reply_markup=get_main_menu_keyboard()
        )


async def check_video_ownership(user_id: int, video_url: str) -> tuple[bool, str, Optional[str]]:
    try:
        from services.youtube_service import get_video_channel_info
        
        channel_info = await get_video_channel_info(video_url)
        
        if not channel_info:
            return False, "Не удалось получить информацию о канале", None
        
        video_channel_url = channel_info['channel_url']
        video_channel_id = channel_info['channel_id']
        video_channel_title = channel_info['channel_title']
        
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
        
        is_owner, ownership_msg, channel_url_to_verify = await check_video_ownership(user_id, url)
        
        if user_id not in ADMIN_IDS:
            if not is_owner:
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
        
        if user_id not in ADMIN_IDS:
            if user.analyses_used >= user.analyses_limit:
                await message.answer(
                    f"❌ Достигнут лимит анализов.\n\n"
                    f"📊 Использовано: {user.analyses_used}/{user.analyses_limit}",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return
        
        progress_msg = await message.answer("⏳ Загрузка комментариев...")
        
        video_id = extract_video_id(url)
        comments_data = get_video_comments(video_id)
        comments_file = get_comments_file_path(video_id)
        comments_len = get_video_comments_count(url)

        if comments_len >= 2000 and analysis_type == "advanced":
            if user.tariff_plan not in ['pro', 'business', 'enterprise'] and user_id not in ADMIN_IDS:
                raise ValueError("❌ Превышен лимит в 2000 комментариев для анализа.")

        save_comments_to_file(comments_data, comments_file)
        
        await update_progress_message(
            progress_msg, 
            f"✅ Загружено {comments_len} комментариев\n🔄 Сохранение в базу данных..."
        )
        
        db_video_id = await create_video(
            user.id, 
            url, 
            f"Comments: {comments_file}"
        )
        
        with open(comments_file, "r", encoding="utf-8") as f:
            comments_text = f.read()
        
        if analysis_type == "simple":
            await update_progress_message(
                progress_msg,
                "🤖 Анализ комментариев через AI...\n⏱ Это может занять 30-60 секунд"
            )
            
            simple_prompts = await get_prompts(category=category, analysis_type="simple")
            if not simple_prompts:
                raise ValueError("Нет промпта для простого анализа")
            
            prompt_text = simple_prompts[0].prompt_text
            ai_response = await analyze_comments_with_prompt(comments_text, prompt_text)
            
            await create_ai_response(
                user.id, 
                db_video_id, 
                0, 
                "simple", 
                ai_response
            )
            
            final_ai_response = ai_response
        
        elif analysis_type == "advanced":
            advanced_prompts = await get_prompts(category=category, analysis_type="advanced")
            if not advanced_prompts:
                raise ValueError("Нет advanced промптов в базе")
            
            total_steps = len(advanced_prompts) + 1
            
            await update_progress_message(
                progress_msg,
                f"🤖 Углубленный анализ ({total_steps} этапов)...\n⏱ Это может занять 2-3 минуты"
            )
            
            partial_responses = []
            
            tasks = []
            for idx, prompt in enumerate(advanced_prompts):
                task = analyze_comments_with_prompt(comments_text, prompt.prompt_text)
                tasks.append((idx, task))
            
            results = await asyncio.gather(*[t[1] for t in tasks])
            
            for idx, partial_response in enumerate(results):
                partial_responses.append(partial_response)
                await create_ai_response(
                    user.id, 
                    db_video_id, 
                    idx + 1,
                    "advanced_partial", 
                    partial_response
                )
                
                completed = idx + 1
                percentage = int((completed / total_steps) * 100)
                progress_bar = "▓" * (percentage // 10) + "░" * (10 - percentage // 10)
                
                await update_progress_message(
                    progress_msg,
                    f"🔍 Этап {completed}/{total_steps}\n{progress_bar} {percentage}%"
                )
            
            await update_progress_message(
                progress_msg,
                f"🔄 Финальный синтез...\n{progress_bar} 90%"
            )
            
            synthesis_prompts = await get_prompts(category=category, analysis_type="synthesis")
            if not synthesis_prompts:
                raise ValueError("Должен быть ровно один synthesis промпт")
            
            synthesis_prompt_text = synthesis_prompts[0].prompt_text
            combined_partials = "\n\n".join(
                [f"ЧАСТИЧНЫЙ ОТВЕТ {i+1}:\n{resp}" for i, resp in enumerate(partial_responses)]
            )
            
            final_ai_response = await analyze_comments_with_prompt(
                combined_partials,
                synthesis_prompt_text
            )
            
            await create_ai_response(
                user.id, 
                db_video_id, 
                0,
                "advanced", 
                final_ai_response
            )
        
        else:
            raise ValueError("Неизвестный тип анализа")
        
        await update_progress_message(
            progress_msg,
            "📄 Генерация PDF отчета..."
        )
        
        pdf_file = generate_pdf(final_ai_response, url, video_id)
        
        reports_dir = Path(f"reports/{user.user_id}")
        reports_dir.mkdir(parents=True, exist_ok=True)
        saved_pdf_path = reports_dir / f"{video_id}_{analysis_type}.pdf"
        os.rename(pdf_file, str(saved_pdf_path))
        pdf_file = str(saved_pdf_path)

        txt_file_path = reports_dir / f"{video_id}_{analysis_type}.txt"
        with open(txt_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(f"=== ANALIZ NATIJALARI ===\n\n")
            txt_file.write(f"Video ID: {video_id}\n")
            txt_file.write(f"Video URL: {url}\n")
            txt_file.write(f"Tahlil turi: {'Oddiy' if analysis_type == 'simple' else 'Chuqur'}\n")
            txt_file.write(f"Kommentlar soni: {comments_len}\n")
            txt_file.write(f"Sana: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            txt_file.write(f"\n{'='*50}\n\n")
            txt_file.write(final_ai_response)
        

        from database.crud import update_ai_response_txt_path
        await update_ai_response_txt_path(user.id, db_video_id, str(txt_file_path))
        
        try:
            channel_info = await get_video_channel_info(url)
            channel_id = channel_info.get('channel_id') if channel_info else None
        except Exception:
            channel_id = None

        from database.crud import update_video_channel_id
        if channel_id:
            await update_video_channel_id(db_video_id, channel_id)
        
        if progress_msg:
            await progress_msg.delete()
            progress_msg = None
        
        await message.answer_document(
            FSInputFile(pdf_file),
            caption=f"📊 <b>Анализ готов!</b>\n\n"
                    f"📹 Видео: <code>{video_id}</code>\n"
                    f"📝 Комментариев: {comments_len}\n"
                    f"🎯 Тип: {'Простой' if analysis_type == 'simple' else 'Углубленный'}\n\n",
            parse_mode="HTML",
        )

        if user_id not in ADMIN_IDS:
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
                f"👑 Вы администратор - безлимитный доступ\n\n"
                f"Выберите действие:",
                reply_markup=get_after_analysis_keyboard()
            )
        
        if user_id not in ADMIN_IDS:
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
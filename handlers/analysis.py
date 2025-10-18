from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback
from states.analysis import AnalysisFSM
from keyboards.client import get_analysis_type_keyboard, get_back_to_menu_keyboard, get_main_menu_keyboard
from services.youtube_service import extract_video_id, get_video_comments, save_comments_to_file, get_comments_file_path
from services.ai_service import analyze_comments_with_prompt
from services.pdf_generator import generate_pdf
from database.crud import get_user, update_user_analyses, create_video, get_prompts, create_ai_response
from utils.texts import ENTER_VIDEO_URL, INVALID_URL, LIMIT_EXCEEDED, ANALYSIS_STARTED, ANALYSIS_DONE
from utils.progress import ProgressTracker
import os
import asyncio
from datetime import datetime
from pathlib import Path

router = Router()

user_analysis_locks = {}

@router.callback_query(MenuCallback.filter(F.action == "analysis_my_video"))
async def analysis_my_video_handler(query: CallbackQuery, state: FSMContext):
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="my")
    await query.message.edit_text("Выберите тип анализа:", reply_markup=get_analysis_type_keyboard("my"))

@router.callback_query(MenuCallback.filter(F.action == "analysis_competitor"))
async def analysis_competitor_handler(query: CallbackQuery, state: FSMContext):
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="competitor")
    await query.message.edit_text("Выберите тип анализа:", reply_markup=get_analysis_type_keyboard("competitor"))

@router.callback_query(AnalysisFSM.choose_type, AnalysisCallback.filter(F.type == "simple"))
async def choose_simple_analysis(query: CallbackQuery, callback_data: AnalysisCallback, state: FSMContext):
    await state.update_data(analysis_type="simple")
    await query.message.edit_text(ENTER_VIDEO_URL, reply_markup=get_back_to_menu_keyboard())
    await state.set_state(AnalysisFSM.waiting_for_url)

@router.callback_query(AnalysisFSM.choose_type, AnalysisCallback.filter(F.type == "advanced"))
async def choose_advanced_analysis(query: CallbackQuery, callback_data: AnalysisCallback, state: FSMContext):
    await state.update_data(analysis_type="advanced")
    await query.message.edit_text(ENTER_VIDEO_URL, reply_markup=get_back_to_menu_keyboard())
    await state.set_state(AnalysisFSM.waiting_for_url)

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


async def run_analysis_task(user_id: int, message: Message, url: str, category: str, analysis_type: str):
    comments_file = None
    pdf_file = None
    progress_msg = None
    
    try:
        user = await get_user(user_id)
        
        if user.analyses_used >= user.analyses_limit:
            await message.answer(LIMIT_EXCEEDED, reply_markup=get_back_to_menu_keyboard())
            return
        
        progress_msg = await message.answer("⏳ Загрузка комментариев с YouTube...")
        
        video_id = extract_video_id(url)
        comments_data = get_video_comments(video_id)
        comments_file = get_comments_file_path(video_id)
        save_comments_to_file(comments_data, comments_file)
        
        await update_progress_message(
            progress_msg, 
            f"✅ Загружено {len(comments_data)} комментариев\n🔄 Сохранение в базу данных..."
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
        
        await update_progress_message(
            progress_msg,
            "✅ Анализ завершен!"
        )
        
        await message.answer_document(
            FSInputFile(pdf_file),
            caption=f"📊 <b>Анализ готов!</b>\n\n"
                    f"📹 Видео: <code>{video_id}</code>\n"
                    f"📝 Комментариев: {len(comments_data)}\n"
                    f"🎯 Тип: {'Простой' if analysis_type == 'simple' else 'Углубленный'}\n\n",
            parse_mode="HTML",
        )

        await message.answer(
            "Вы можете продолжить использовать бот:",
            reply_markup=get_main_menu_keyboard()
        )
        
        # await update_user_analyses(user.id, user.analyses_used + 1)
        
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
        import traceback
        print(traceback.format_exc())


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
    
    if not category or not analysis_type:
        await message.answer(
            "❌ Ошибка: не выбран тип анализа.\n\n"
            "Пожалуйста, начните заново:",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return
    
    await state.clear()
    
    # Asinxron task yaratish
    task = asyncio.create_task(
        run_analysis_task(user_id, message, url, category, analysis_type)
    )
    user_analysis_locks[user_id] = task
    
    def cleanup(t):
        if user_id in user_analysis_locks:
            del user_analysis_locks[user_id]
    
    task.add_done_callback(cleanup)
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from callbacks.admin import AdminCallback
from keyboards.client import get_main_menu_keyboard
from keyboards.admin import get_admin_menu_keyboard
from database.crud import get_user, create_video, create_ai_response, update_user_analyses, get_prompts, create_prompt, update_prompt, delete_prompt
from services.sample_report_service import SampleReportsService
from services.youtube_service import extract_video_id, is_shorts_url, get_video_comments_adaptive
from services.shorts_preprocessor import RawDataShortsPreprocessor
from services.ai_service import analyze_comments_with_prompt
from services.pdf_generator import generate_pdf
from states.analysis import AnalysisFSM
from states.admin import AdminFSM
from datetime import datetime
from pathlib import Path
import os
import io

router = Router()

from config import Config
config = Config()
ADMIN_IDS = config.ADMIN_IDS


def get_shorts_analysis_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Автоматический анализ", callback_data="shorts:auto_level")
    builder.button(text="📊 Выбрать уровень вручную", callback_data="shorts:manual_level")
    builder.button(text="📈 Показать прогрессию", callback_data="shorts:show_progression")
    builder.button(text="⬅️ Назад", callback_data=MenuCallback(action="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_shorts_level_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="1️⃣ Базовый анализ эмоций", callback_data="shorts:level:1")
    builder.button(text="2️⃣ Стратегическая оптимизация", callback_data="shorts:level:2")
    builder.button(text="3️⃣ Анализ зацепляющих моментов", callback_data="shorts:level:3")
    builder.button(text="4️⃣ Виральный потенциал", callback_data="shorts:level:4")
    builder.button(text="5️⃣ Контент-план на будущее", callback_data="shorts:level:5")
    builder.button(text="⬅️ Назад", callback_data=MenuCallback(action="analyze_shorts"))
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(MenuCallback.filter(F.action == "analyze_shorts"))
async def analyze_shorts_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    
    user = await get_user(query.from_user.id)
    
    if not user:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    text = f"""
🎬 <b>АНАЛИЗ YOUTUBE SHORTS</b>

Shorts - это особый формат с быстрой динамикой.

📊 <b>АДАПТИВНАЯ СИСТЕМА:</b>

🟢 <b>До 300 комментариев</b>
• Полный глубинный анализ
• Детальная эмоциональная карта

🟡 <b>300-1000 комментариев</b>
• Умная выборка
• Расширенные инсайты

🔴 <b>1000+ комментариев</b>
• Стратегический анализ
• Быстрый результат

🔄 <b>ПРОГРЕССИВНЫЕ УРОВНИ:</b>

<b>Уровень 1:</b> Базовые эмоции
<b>Уровень 2:</b> Стратегическая оптимизация
<b>Уровень 3:</b> Анализ зацепляющих моментов
<b>Уровень 4:</b> Виральный потенциал
<b>Уровень 5:</b> Генерация контент-плана

<b>Отправьте ссылку на Shorts ⬇️</b>
"""
    
    await query.message.edit_text(
        text,
        reply_markup=get_shorts_analysis_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "shorts:auto_level")
async def shorts_auto_level_handler(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "🎯 <b>АВТОМАТИЧЕСКИЙ РЕЖИМ</b>\n\n"
        "Система автоматически определит уровень.\n\n"
        "📎 Отправьте ссылку на Shorts:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder()
        .button(text="⬅️ Назад", callback_data=MenuCallback(action="analyze_shorts"))
        .as_markup()
    )
    await state.update_data(shorts_level_mode="auto")
    await state.set_state(AnalysisFSM.waiting_for_shorts_url)


@router.callback_query(F.data == "shorts:manual_level")
async def shorts_manual_level_handler(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "📊 <b>ВЫБОР УРОВНЯ</b>\n\n"
        "Выберите уровень анализа:\n\n"
        "<b>1️⃣ Базовый:</b> Эмоции и реакции\n"
        "<b>2️⃣ Стратегический:</b> Оптимизация\n"
        "<b>3️⃣ Хуки:</b> Что цепляет\n"
        "<b>4️⃣ Виральный:</b> Потенциал\n"
        "<b>5️⃣ Контент-план:</b> Идеи",
        parse_mode="HTML",
        reply_markup=get_shorts_level_keyboard()
    )


@router.callback_query(F.data.startswith("shorts:level:"))
async def shorts_level_selected_handler(query: CallbackQuery, state: FSMContext):
    level = int(query.data.split(":")[-1])
    
    level_names = {
        1: "Базовый анализ эмоций",
        2: "Стратегическая оптимизация",
        3: "Анализ зацепляющих моментов",
        4: "Виральный потенциал",
        5: "Контент-план"
    }
    
    await state.update_data(shorts_level_mode="manual", shorts_level=level)
    
    await query.message.edit_text(
        f"✅ <b>УРОВЕНЬ ВЫБРАН</b>\n\n"
        f"📊 Уровень {level}: {level_names[level]}\n\n"
        f"📎 Отправьте ссылку на Shorts:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder()
        .button(text="⬅️ Изменить", callback_data="shorts:manual_level")
        .button(text="🏠 Меню", callback_data=MenuCallback(action="main_menu"))
        .adjust(1)
        .as_markup()
    )
    await state.set_state(AnalysisFSM.waiting_for_shorts_url)


@router.callback_query(F.data == "shorts:show_progression")
async def shorts_progression_handler(query: CallbackQuery):
    text = """
📊 <b>ПАНЕЛЬ ПРОГРЕССИИ</b>

🔄 <b>Ваш прогресс:</b>
• Уровень 1: ✅ Завершен
• Уровень 2: ⏳ В процессе
• Уровень 3: 🔒 Заблокирован
• Уровень 4: 🔒 Заблокирован
• Уровень 5: 🔒 Заблокирован

💡 <b>Рекомендация:</b>
Завершите уровень 2 для разблокировки 3!
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Продолжить", callback_data=MenuCallback(action="analyze_shorts"))
    builder.button(text="⬅️ Назад", callback_data=MenuCallback(action="analyze_shorts"))
    builder.adjust(1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(AnalysisFSM.waiting_for_shorts_url)
async def process_shorts_url(message: Message, state: FSMContext):
    url = message.text.strip()
    user = await get_user(message.from_user.id)

    if not is_shorts_url(url):
        await message.answer(
            "⚠️ <b>ЭТО НЕ SHORTS</b>\n\n"
            "Это обычное видео.\n\n"
            "Shorts формат:\n"
            "<code>youtube.com/shorts/VIDEO_ID</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder()
            .button(text="📹 Обычное видео", callback_data=MenuCallback(action="analysis_my_video"))
            .button(text="🔄 Отправить Shorts", callback_data=MenuCallback(action="analyze_shorts"))
            .adjust(1)
            .as_markup()
        )
        return
    
    is_admin = message.from_user.id in ADMIN_IDS
    
    if not is_admin and user.analyses_used >= user.analyses_limit:
        await send_shorts_demo_report(message, user.user_id)
        await state.clear()
        return
    
    progress_msg = await message.answer("⏳ Запускаем анализ Shorts...")
    
    try:

        video_id = extract_video_id(url)
        await progress_msg.edit_text("📥 Загрузка комментариев...")
        
        raw_comments = get_video_comments_adaptive(video_id, url)
        
        await progress_msg.edit_text(
            f"🧹 Очистка...\n"
            f"Найдено: {len(raw_comments)}"
        )
        
        preprocessor = RawDataShortsPreprocessor()
        cleaned_comments = preprocessor.clean_comments(raw_comments)
        
        total_comments = len(cleaned_comments)
        
        if total_comments <= 300:
            scale = "small"
            scale_emoji = "🟢"
            scale_name = "полный"
        elif total_comments <= 1000:
            scale = "medium"
            scale_emoji = "🟡"
            scale_name = "расширенный"
        else:
            scale = "large"
            scale_emoji = "🔴"
            scale_name = "стратегический"
        
        await progress_msg.edit_text(
            f"✅ Очистка завершена\n"
            f"📊 Комментариев: {total_comments}\n"
            f"{scale_emoji} Режим: {scale_name}\n\n"
            f"🤖 Запуск AI..."
        )
        
        state_data = await state.get_data()
        level_mode = state_data.get('shorts_level_mode', 'auto')
        
        if level_mode == 'auto':
            analysis_level = 1 
        else:
            analysis_level = state_data.get('shorts_level', 1)
        
        analysis_type = f"shorts_{scale}_{500 + analysis_level}"
        prompts = await get_prompts(category="shorts", analysis_type=analysis_type)
        
        if not prompts:
            await progress_msg.edit_text(
                f"❌ Промпт не найден\n\n"
                f"Тип: {analysis_type}",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return
        
        prompt_text = prompts[0].prompt_text
        
        await progress_msg.edit_text(
            f"{scale_emoji} Анализ уровня {analysis_level}\n"
            f"⏳ Обработка {total_comments}..."
        )
        
        comments_text = "\n\n".join([
            f"[{c['time']}] ({c['author']}, {c['likes']} likes) {c['text']}"
            for c in cleaned_comments
        ])
        
        analysis_result = await analyze_comments_with_prompt(comments_text, prompt_text)
        
        db_video_id = await create_video(
            user.id,
            url,
            f"Shorts: {video_id}"
        )
        
        await create_ai_response(
            user.id,
            db_video_id,
            0,
            f"shorts_level_{analysis_level}",
            analysis_result
        )
        
        await progress_msg.edit_text("📄 Генерация PDF...")
        
        pdf_file = generate_pdf(analysis_result, url, video_id)
        
        reports_dir = Path(f"reports/{user.user_id}/shorts")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_pdf_path = reports_dir / f"{video_id}_shorts_lv{analysis_level}_{timestamp}.pdf"
        os.rename(pdf_file, str(saved_pdf_path))
        
        await progress_msg.delete()
        
        await message.answer_document(
            FSInputFile(str(saved_pdf_path)),
            caption=f"📊 <b>Анализ Shorts готов!</b>\n\n"
                    f"🎬 Видео: <code>{video_id}</code>\n"
                    f"📊 Комментариев: {total_comments}\n"
                    f"{scale_emoji} Режим: {scale_name}\n"
                    f"🎯 Уровень: {analysis_level}\n"
                    f"🗑️ Удалено шума: {len(raw_comments) - len(cleaned_comments)}",
            parse_mode="HTML"
        )
        
        if not is_admin:
            await update_user_analyses(user.user_id, user.analyses_used + 1)
            
            remaining = user.analyses_limit - (user.analyses_used + 1)
            await message.answer(
                f"✅ Анализ завершен!\n\n"
                f"📊 Осталось: {remaining}/{user.analyses_limit}",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "✅ Анализ завершен!\n\n"
                "👑 Админ режим",
                reply_markup=get_main_menu_keyboard()
            )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        await progress_msg.edit_text(
            f"❌ <b>ОШИБКА</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()


async def send_shorts_demo_report(message: Message, user_id: int):
    sample_report = await SampleReportsService.get_random_sample_report(video_type='shorts')
    
    if not sample_report:
        await message.answer(
            "❌ Демо отчеты недоступны.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await message.answer(
        "📊 <b>ДЕМО АНАЛИЗ SHORTS</b>\n\n"
        "На бесплатном тарифе демо-версия.\n\n"
        "<i>Это образец для ознакомления.</i>",
        parse_mode="HTML"
    )
    
    analysis_data = sample_report['analysis_data']
    pdf_path = analysis_data.get('pdf_path')
    
    if pdf_path and os.path.exists(pdf_path):
        await message.answer_document(
            FSInputFile(pdf_path),
            caption="📊 <b>ДЕМО Shorts готов!</b>\n\n"
                    "<i>Подтвердите канал для реальных анализов!</i>",
            parse_mode="HTML"
        )



@router.callback_query(AdminCallback.filter(F.action == "manage_shorts_prompts"))
async def manage_shorts_prompts(query: CallbackQuery):
    total_prompts = 0
    for scale in ['small', 'medium', 'large']:
        for level in range(501, 506):
            prompts = await get_prompts(category="shorts", analysis_type=f"shorts_{scale}_{level}")
            if prompts:
                total_prompts += 1
    
    text = f"""
🎬 <b>ПРОМПТЫ ДЛЯ SHORTS</b>

📊 <b>Всего промптов:</b> {total_prompts}/15

Shorts имеет 3 масштаба:
- 🟢 Малый (&lt;300 комментов)
- 🟡 Средний (300-1000)
- 🔴 Большой (1000+)

Каждый масштаб имеет 5 уровней (501-505):
• 501: Базовый анализ эмоций
• 502: Стратегическая оптимизация
• 503: Анализ зацепляющих моментов
• 504: Виральный потенциал
• 505: Контент-план на будущее

<b>Выберите масштаб для управления:</b>
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Малый масштаб", callback_data="shorts_prompts:small_scale")
    builder.button(text="🟡 Средний масштаб", callback_data="shorts_prompts:medium_scale")
    builder.button(text="🔴 Большой масштаб", callback_data="shorts_prompts:large_scale")
    builder.button(text="⬅️ Назад", callback_data=AdminCallback(action="back").pack())
    builder.adjust(1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("shorts_prompts:"))
async def shorts_prompts_scale(query: CallbackQuery):
    scale = query.data.split(":")[-1]
    await shorts_prompts_scale_refresh(query, scale)


async def shorts_prompts_scale_refresh(query: CallbackQuery, scale: str):
    scale_names = {
        'small': '🟢 Малый (&lt;300)',
        'medium': '🟡 Средний (300-1000)',
        'large': '🔴 Большой (1000+)'
    }
    
    existing_prompts = {}
    for level in range(501, 506):
        analysis_type = f"shorts_{scale}_{level}"
        prompts = await get_prompts(category="shorts", analysis_type=analysis_type)
        existing_prompts[level] = prompts[0] if prompts else None
    
    text = f"""
{scale_names[scale]}

<b>📋 Статус промптов:</b>

"""
    
    builder = InlineKeyboardBuilder()
    
    for level in range(501, 506):
        level_names = {
            501: "Базовый анализ",
            502: "Стратегическая оптимизация",
            503: "Анализ хуков",
            504: "Виральный потенциал",
            505: "Контент-план"
        }
        
        prompt = existing_prompts[level]
        
        if prompt:
            status = "✅"
            text += f"{status} <b>{level}:</b> {level_names[level]}\n"
            
            builder.button(
                text=f"👁 {level}",
                callback_data=f"view_shorts_prompt:{scale}:{level}"
            )
            builder.button(
                text=f"🗑 {level}",
                callback_data=f"delete_shorts_prompt:{scale}:{level}:{prompt.id}"
            )
        else:
            status = "❌"
            text += f"{status} <b>{level}:</b> {level_names[level]} (нет)\n"
            
            builder.button(
                text=f"➕ {level}",
                callback_data=f"upload_shorts:{scale}:{level}"
            )
    
    text += f"\n<i>👁 - Просмотр | 🗑 - Удалить | ➕ - Добавить</i>"
    
    builder.adjust(2)
    builder.row(
        InlineKeyboardBuilder().button(
            text="⬅️ Назад",
            callback_data=AdminCallback(action="manage_shorts_prompts").pack()
        ).as_markup().inline_keyboard[0][0]
    )
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("view_shorts_prompt:"))
async def view_shorts_prompt_handler(query: CallbackQuery):
    parts = query.data.split(":")
    scale = parts[1]
    level = parts[2]
    
    analysis_type = f"shorts_{scale}_{level}"
    prompts = await get_prompts(category="shorts", analysis_type=analysis_type)
    
    if not prompts:
        await query.answer("❌ Промпт не найден", show_alert=True)
        return
    
    prompt = prompts[0]
    
    prompt_preview = prompt.prompt_text[:1000] + "..." if len(prompt.prompt_text) > 1000 else prompt.prompt_text
    
    text = f"""
📄 <b>SHORTS PROMPT</b>

🎯 <b>Масштаб:</b> {scale}
📊 <b>Уровень:</b> {level}
🆔 <b>ID:</b> {prompt.id}
📝 <b>Название:</b> {prompt.name}
📏 <b>Длина:</b> {len(prompt.prompt_text)} символов

<b>Превью:</b>
<code>{prompt_preview}</code>
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Обновить", callback_data=f"update_shorts_prompt:{scale}:{level}:{prompt.id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_shorts_prompt:{scale}:{level}:{prompt.id}")
    builder.button(text="⬅️ Назад", callback_data=f"shorts_prompts:{scale}")
    builder.adjust(2, 1)
    
    await query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("delete_shorts_prompt:"))
async def delete_shorts_prompt_handler(query: CallbackQuery):
    parts = query.data.split(":")
    scale = parts[1]
    level = parts[2]
    prompt_id = int(parts[3])
    
    try:
        await delete_prompt(prompt_id)
        await query.answer("✅ Промпт удален!", show_alert=True)
        await shorts_prompts_scale_refresh(query, scale)
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


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


@router.callback_query(F.data.startswith("update_shorts_prompt:"))
async def update_shorts_prompt_handler(query: CallbackQuery, state: FSMContext):
    parts = query.data.split(":")
    scale = parts[1]
    level = parts[2]
    prompt_id = int(parts[3])
    
    await state.update_data(
        shorts_scale=scale,
        shorts_level=level,
        updating_prompt_id=prompt_id
    )
    
    await query.message.edit_text(
        f"📤 <b>ОБНОВЛЕНИЕ ПРОМПТА</b>\n\n"
        f"Масштаб: {scale}\n"
        f"Уровень: {level}\n\n"
        f"Отправьте новый .txt файл:",
        parse_mode="HTML"
    )
    await state.set_state(AdminFSM.waiting_for_shorts_prompt_update)


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


@router.message(AdminFSM.waiting_for_shorts_prompt_update)
async def process_shorts_prompt_update(message: Message, state: FSMContext, bot: Bot):
    if not message.document or message.document.mime_type != 'text/plain':
        await message.answer("❌ Отправьте .txt файл")
        return
    
    data = await state.get_data()
    scale = data['shorts_scale']
    level = data['shorts_level']
    prompt_id = data['updating_prompt_id']
    
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
    
    await update_prompt(prompt_id, prompt_text)
    
    await message.answer(
        f"✅ <b>ПРОМПТ ОБНОВЛЕН</b>\n\n"
        f"📊 Масштаб: {scale}\n"
        f"🎯 Уровень: {level}\n"
        f"🆔 ID: {prompt_id}\n"
        f"📏 Новая длина: {len(prompt_text)} символов",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from keyboards.client import get_cabinet_keyboard, get_history_keyboard, get_back_to_cabinet_keyboard
from database.crud import get_user, get_user_videos_history, get_video_by_id, get_ai_response_by_video
from services.pdf_generator import generate_pdf
from utils.helpers import safe_edit_text
from pathlib import Path
import os

router = Router()


@router.callback_query(F.data == "personal_cabinet")
async def personal_cabinet_handler(query: CallbackQuery):
    
    user = await get_user(query.from_user.id)
    
    if not user:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    cabinet_text = (
        f"⚙️ <b>Личный кабинет</b>\n\n"
        f"👤 Пользователь: {user.username or 'Не указано'}\n"
        f"📊 Тариф: {'Premium' if user.tariff_plan else 'Basic'}\n"
        f"📈 Использовано анализов: {user.analyses_used}/{user.analyses_limit}\n"
        f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        f"Выберите действие:"
    )
    
    await safe_edit_text(
        query,
        cabinet_text,
        reply_markup=get_cabinet_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cabinet:history")
async def history_handler(query: CallbackQuery, state: FSMContext):
    
    await show_history_page(query, page=1)


@router.callback_query(F.data.startswith("history:page:"))
async def history_page_handler(query: CallbackQuery):
    
    page = int(query.data.split(":")[-1])
    await show_history_page(query, page)


async def show_history_page(query: CallbackQuery, page: int = 1):
    
    user = await get_user(query.from_user.id)
    
    if not user:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    limit = 5
    offset = (page - 1) * limit
    
    videos, total_count = await get_user_videos_history(
        query.from_user.id,
        limit=limit,
        offset=offset
    )
    
    if not videos:
        await safe_edit_text(
            query,
            "📋 <b>История отчетов</b>\n\n"
            "У вас пока нет сохраненных отчетов.\n"
            "Создайте первый анализ!",
            reply_markup=get_back_to_cabinet_keyboard(),
            parse_mode="HTML"
        )
        return
    
   
    history_text = f"📋 <b>История отчетов</b>\n\n"
    history_text += f"Всего отчетов: {total_count}\n"
    history_text += f"Страница {page} из {(total_count + limit - 1) // limit}\n\n"
    
    for idx, (video, ai_response) in enumerate(videos, start=1):
        video_id = video.video_url.split('v=')[-1] if 'v=' in video.video_url else video.video_url.split('/')[-1]
        analysis_type = ai_response.analysis_type if ai_response else "N/A"
        analysis_type_ru = "Простой" if analysis_type == "simple" else "Расширенный" if analysis_type == "advanced" else analysis_type
        
        history_text += (
            f"{offset + idx}. 📹 <code>{video_id[:11]}</code>\n"
            f"   📅 {video.processed_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   🎯 Тип: {analysis_type_ru}\n\n"
        )
    
    total_pages = (total_count + limit - 1) // limit
    
    await safe_edit_text(
        query,
        history_text,
        reply_markup=get_history_keyboard(page, total_pages, videos),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("download:"))
async def download_report_handler(query: CallbackQuery):
    
    video_db_id = int(query.data.split(":")[-1])
    
    video = await get_video_by_id(video_db_id)
    if not video:
        await query.answer("❌ Видео не найдено", show_alert=True)
        return
    
    ai_response = await get_ai_response_by_video(video_db_id)
    if not ai_response:
        await query.answer("❌ Отчет не найден", show_alert=True)
        return
    
    
    video_id = video.video_url.split('v=')[-1] if 'v=' in video.video_url else video.video_url.split('/')[-1]
    user = await get_user(query.from_user.id)
    
    pdf_path = Path(f"reports/{user.user_id}/{video_id}_{ai_response.analysis_type}.pdf")
    
    if not pdf_path.exists():
        await query.answer("⏳ Генерация PDF...", show_alert=True)
        pdf_file = generate_pdf(ai_response.response_text, video.video_url, video_id)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        os.rename(pdf_file, str(pdf_path))
    
    try:
        await query.message.answer_document(
            FSInputFile(pdf_path),
            caption=f"📊 Отчет для видео: <code>{video_id}</code>\n"
                    f"📅 Дата: {video.processed_at.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
        await query.answer("✅ Отчет отправлен!")
    except Exception as e:
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "cabinet:upgrade_tariff")
async def upgrade_tariff_handler(query: CallbackQuery):
    await query.answer("💳 Функция улучшения тарифа в разработке", show_alert=True)


@router.callback_query(F.data == "cabinet:notifications")
async def notifications_handler(query: CallbackQuery):
    await query.answer("🔔 Функция настройки уведомлений в разработке", show_alert=True)


@router.callback_query(F.data == "cabinet:integrations")
async def integrations_handler(query: CallbackQuery):
    await query.answer("🤖 Функция интеграций в разработке", show_alert=True)


@router.callback_query(F.data == "cabinet:competitors")
async def competitors_handler(query: CallbackQuery):
    await query.answer("👥 Функция управления конкурентами в разработке", show_alert=True)
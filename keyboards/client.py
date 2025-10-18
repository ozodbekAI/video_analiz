from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Анализ моего видео", callback_data=MenuCallback(action="analysis_my_video").pack()),
        InlineKeyboardButton(text="🥊 Анализ конкурента", callback_data=MenuCallback(action="analysis_competitor").pack())
    )
    builder.row(
        InlineKeyboardButton(text="❤️ Индекс здоровья", callback_data=MenuCallback(action="health_index").pack()),
        InlineKeyboardButton(text="📊 Динамика канала", callback_data=MenuCallback(action="channel_dynamics").pack())
    )
    builder.row(
        InlineKeyboardButton(text="🎬 Генератор контента", callback_data=MenuCallback(action="content_generator").pack()),
        InlineKeyboardButton(text="🚨 Кризис-менеджер (Премиум)", callback_data=MenuCallback(action="crisis_manager").pack())
    )
    builder.row(
        InlineKeyboardButton(text="👤 Карта личности (Премиум)", callback_data=MenuCallback(action="personality_map").pack()),
        InlineKeyboardButton(text="🔍 Детектор трендов (Премиум)", callback_data=MenuCallback(action="trend_detector").pack())
    )
    builder.row(
        InlineKeyboardButton(text="📝 Генератор заголовков (Премиум)", callback_data=MenuCallback(action="title_generator").pack()),
        InlineKeyboardButton(text="🖼️ Генератор обложек (Премиум)", callback_data=MenuCallback(action="cover_generator").pack())
    )
    builder.row(
        InlineKeyboardButton(text="📅 Планировщик стратегии (Премиум)", callback_data=MenuCallback(action="strategy_planner").pack()),
        InlineKeyboardButton(text="💰 Мониторинг монетизации (Премиум)", callback_data=MenuCallback(action="monetization_monitor").pack())
    )
    builder.row(
        InlineKeyboardButton(text="💪 Мотивация", callback_data=MenuCallback(action="motivation").pack()),
        InlineKeyboardButton(text="⚙️ Личный кабинет", callback_data="personal_cabinet")
    )
    return builder.as_markup()

def get_analysis_type_keyboard(category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⛏️Простой анализ", callback_data=AnalysisCallback(type="simple", category=category).pack()))
    builder.row(InlineKeyboardButton(text="⚙️Расширенный анализ", callback_data=AnalysisCallback(type="advanced", category=category).pack()))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data=MenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_cabinet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Улучшить тариф", callback_data="cabinet:upgrade_tariff"),
        InlineKeyboardButton(text="🔔 Настроить уведомления", callback_data="cabinet:notifications")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Настроить интеграции", callback_data="cabinet:integrations"),
        InlineKeyboardButton(text="👥 Управление конкурентами", callback_data="cabinet:competitors")
    )
    builder.row(
        InlineKeyboardButton(text="📋 История отчетов", callback_data="cabinet:history"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())
    )
    return builder.as_markup()

def get_history_keyboard(current_page: int, total_pages: int, videos: list) -> InlineKeyboardMarkup:
    
    builder = InlineKeyboardBuilder()
    
    
    for video, ai_response in videos:
        video_id = video.video_url.split('v=')[-1] if 'v=' in video.video_url else video.video_url.split('/')[-1]
        builder.row(
            InlineKeyboardButton(
                text=f"📥 Скачать {video_id[:11]}",
                callback_data=f"download:{video.id}"
            )
        )
    
    pagination_buttons = []
    if current_page > 1:
        pagination_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"history:page:{current_page - 1}")
        )
    if current_page < total_pages:
        pagination_buttons.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"history:page:{current_page + 1}")
        )
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
    
    
    builder.row(
        InlineKeyboardButton(text="↩️ Назад в кабинет", callback_data="personal_cabinet")
    )
    
    return builder.as_markup()


def get_back_to_cabinet_keyboard() -> InlineKeyboardMarkup:
   
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Назад в кабинет", callback_data="personal_cabinet")
    )
    return builder.as_markup()
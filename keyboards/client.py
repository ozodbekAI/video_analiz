from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback


def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data=MenuCallback(action="select_language", category="ru"))
    builder.button(text="🇺🇸 English", callback_data=MenuCallback(action="select_language", category="en"))
    builder.button(text="🇧🇷 Português", callback_data=MenuCallback(action="select_language", category="pt"))
    builder.button(text="🇫🇷 Français", callback_data=MenuCallback(action="select_language", category="fr"))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Анализ моего видео", callback_data=MenuCallback(action="analysis_my_video"))
    builder.button(text="🥊 Анализ конкурента", callback_data=MenuCallback(action="analysis_competitor"))
    builder.button(text="📊 Стратегический хаб", callback_data=MenuCallback(action="strategic_hub"))
    builder.button(text="💪 Мотивация", callback_data=MenuCallback(action="motivation"))
    builder.button(text="⚙️ Личный кабинет", callback_data="personal_cabinet")
    builder.adjust(1)
    return builder.as_markup()


def get_strategic_hub_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Эволюция контента", callback_data=MenuCallback(action="content_evolution"))
    builder.button(text="👥 Карта аудитории", callback_data=MenuCallback(action="audience_map"))
    builder.button(text="🚨 Мониторинг рисков", callback_data=MenuCallback(action="risk_monitoring"))
    builder.button(text="💪 Сильные стороны", callback_data=MenuCallback(action="strengths"))
    builder.button(text="🎯 План роста", callback_data=MenuCallback(action="growth_plan"))
    builder.button(text="📉 Детектор аномалий", callback_data=MenuCallback(action="anomaly_detector"))
    builder.button(text="↩️ Назад", callback_data=MenuCallback(action="main_menu"))
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_analysis_type_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⛏️ Простой анализ", 
        callback_data=AnalysisCallback(type="simple", category=category)
    )
    builder.button(
        text="⚙️ Углубленный анализ", 
        callback_data=AnalysisCallback(type="advanced", category=category)
    )
    builder.button(text="↩️ Назад", callback_data=MenuCallback(action="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_after_analysis_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu"))
    builder.button(text="⚙️ Личный кабинет", callback_data="personal_cabinet")
    builder.button(text="🧑🏼‍💻 Техподдержка", callback_data="support", url="https://t.me/sp_alexey")
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu"))
    return builder.as_markup()


def get_cabinet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 История отчетов", callback_data="cabinet:history")
    builder.button(text="💳 Улучшить тариф", callback_data="cabinet:upgrade_tariff")
    builder.button(text="🔔 Уведомления", callback_data="cabinet:notifications")
    builder.button(text="🤖 Интеграции", callback_data="cabinet:integrations")
    builder.button(text="👥 Конкуренты", callback_data="cabinet:competitors")
    builder.button(text="🌐 Изменить язык", callback_data="cabinet:change_language")  # Yangi tugma
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_history_keyboard(current_page: int, total_pages: int, videos: list):
    builder = InlineKeyboardBuilder()
    
    for video, ai_response in videos:
        video_id = video.video_url.split('v=')[-1] if 'v=' in video.video_url else video.video_url.split('/')[-1]
        builder.button(
            text=f"📄 {video_id[:11]}", 
            callback_data=f"download:{video.id}"
        )
    
    builder.adjust(2)
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data=f"history:page:{current_page-1}"
        ))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️", 
            callback_data=f"history:page:{current_page+1}"
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(
        text="↩️ Назад в кабинет", 
        callback_data="personal_cabinet"
    ))
    
    return builder.as_markup()


def get_back_to_cabinet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад в кабинет", callback_data="personal_cabinet")
    return builder.as_markup()
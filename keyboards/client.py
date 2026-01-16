# keyboards/client.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks.menu import MenuCallback
from callbacks.analysis import AnalysisCallback


def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🇷🇺 Русский",
        callback_data=MenuCallback(action="select_language", category="ru").pack(),
    )
    builder.button(
        text="🇺🇸 English",
        callback_data=MenuCallback(action="select_language", category="en").pack(),
    )
    builder.button(
        text="🇧🇷 Português",
        callback_data=MenuCallback(action="select_language", category="pt").pack(),
    )
    builder.button(
        text="🇫🇷 Français",
        callback_data=MenuCallback(action="select_language", category="fr").pack(),
    )
    builder.adjust(2, 2)
    return builder.as_markup()


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Анализ Shorts", callback_data=MenuCallback(action="analyze_shorts").pack())
    builder.button(text="📈 Анализ моего видео", callback_data=MenuCallback(action="analysis_my_video").pack())
    builder.button(text="🥊 Анализ конкурента", callback_data=MenuCallback(action="analysis_competitor").pack())
    builder.button(text="📊 Стратегический хаб", callback_data=MenuCallback(action="strategic_hub").pack())

    # bu oddiy string bo‘lsa ham mumkin (alohida handler bo‘lsa)
    builder.button(text="⚙️ Личный кабинет", callback_data="personal_cabinet")

    builder.adjust(1)
    return builder.as_markup()


def get_strategic_hub_keyboard():
    # bu yerda siz InlineKeyboardMarkup qo‘lda yig‘yapsiz,
    # shuning uchun callback_data ham 100% str bo‘lishi kerak.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺️ Карта аудитории", callback_data="audience_map")],
            [InlineKeyboardButton(text="🔮 Предсказание контента", callback_data="content_prediction")],
            [InlineKeyboardButton(text="📊 Диагностика канала", callback_data="channel_diagnostics")],
            [InlineKeyboardButton(text="💡 Генератор идей", callback_data="content_ideas")],
            [InlineKeyboardButton(text="⚡ Виральный потенциал", callback_data="viral_potential")],
            [InlineKeyboardButton(text="🧠 Итеративный генератор", callback_data="iterative_ideas")],

            # ✅ ASOSIY FIX SHU:
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())],
        ]
    )


def get_analysis_type_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⛏️ Простой анализ",
        callback_data=AnalysisCallback(type="simple", category=category).pack(),
    )
    builder.button(
        text="⚙️ Углубленный анализ",
        callback_data=AnalysisCallback(type="advanced", category=category).pack(),
    )
    builder.button(text="↩️ Назад", callback_data=MenuCallback(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()


def get_after_analysis_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())
    builder.button(text="⚙️ Личный кабинет", callback_data="personal_cabinet")

    # ❗ URL button’da callback_data BO‘LMASIN (Telegram qoidasi)
    builder.button(text="🧑🏼‍💻 Техподдержка", url="https://t.me/sp_alexey")

    builder.adjust(1)
    return builder.as_markup()


def get_stop_analysis_keyboard():
    """Keyboard shown while analysis is running."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⛔ Остановить анализ", callback_data="analysis:stop")
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())
    return builder.as_markup()


def get_cabinet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 История отчетов", callback_data="cabinet:history")
    builder.button(text="💳 Улучшить тариф", callback_data="cabinet:upgrade_tariff")
    builder.button(text="🔔 Уведомления", callback_data="cabinet:notifications")
    builder.button(text="🤖 Интеграции", callback_data="cabinet:integrations")
    builder.button(text="👥 Конкуренты", callback_data="cabinet:competitors")
    builder.button(text="🌐 Изменить язык", callback_data="cabinet:change_language")

    builder.button(text="🏠 Главное меню", callback_data=MenuCallback(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()


def get_history_keyboard(current_page: int, total_pages: int, videos: list):
    builder = InlineKeyboardBuilder()

    for video, ai_response in videos:
        video_id = video.video_url.split("v=")[-1] if "v=" in video.video_url else video.video_url.split("/")[-1]
        builder.button(
            text=f"📄 {video_id[:11]}",
            callback_data=f"download:{video.id}",
        )

    builder.adjust(2)

    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"history:page:{current_page-1}")
        )

    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперед ▶️", callback_data=f"history:page:{current_page+1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="↩️ Назад в кабинет", callback_data="personal_cabinet")
    )

    return builder.as_markup()


def get_back_to_cabinet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад в кабинет", callback_data="personal_cabinet")
    return builder.as_markup()

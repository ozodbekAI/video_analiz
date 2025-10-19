from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.admin import AdminCallback


def get_admin_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data=AdminCallback(action="view_stats"))
    builder.button(text="📋 Промпты", callback_data=AdminCallback(action="view_prompts"))
    builder.button(text="➕ Добавить промпт", callback_data=AdminCallback(action="add_prompt"))
    builder.button(text="👥 Управление пользователями", callback_data=AdminCallback(action="manage_users"))  # YANGI
    builder.adjust(2, 2)
    return builder.as_markup()


def get_user_management_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Установить лимит", callback_data=AdminCallback(action="set_limit"))
    builder.button(text="🔄 Сбросить использование", callback_data=AdminCallback(action="reset_usage"))
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    builder.adjust(2, 1)
    return builder.as_markup()

def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    return builder.as_markup()


def get_stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data=AdminCallback(action="view_stats"))
    builder.button(text="🏆 Топ пользователей", callback_data=AdminCallback(action="top_users"))
    builder.button(text="📹 Последние анализы", callback_data=AdminCallback(action="recent_videos"))
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_prompt_category_keyboard(add_mode: bool = False):
    builder = InlineKeyboardBuilder()
    action_prefix = "add_select_category" if add_mode else "select_category"
    builder.button(text="Моё видео", callback_data=AdminCallback(action=action_prefix, category="my"))
    builder.button(text="Конкурент", callback_data=AdminCallback(action=action_prefix, category="competitor"))
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_prompt_type_keyboard(add_mode: bool = False):
    builder = InlineKeyboardBuilder()
    action_prefix = "add_select_type" if add_mode else "select_type"
    builder.button(text="⛏️ Простой", callback_data=AdminCallback(action=action_prefix, analysis_type="simple"))
    builder.button(text="⚙️ Углубленный", callback_data=AdminCallback(action=action_prefix, analysis_type="advanced"))
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_advanced_subtype_keyboard(category: str = "my", add_mode: bool = False):
    builder = InlineKeyboardBuilder()
    action_prefix = "add_select_subtype" if add_mode else "select_subtype"
    builder.button(text="📝 Предыдущие промпты", callback_data=AdminCallback(action=action_prefix, subtype="advanced", category=category))
    builder.button(text="🔄 Финальный синтез", callback_data=AdminCallback(action=action_prefix, subtype="synthesis", category=category))
    builder.button(text="↩️ Назад", callback_data=AdminCallback(action="back"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_prompts_keyboard(prompts, analysis_type: str, category: str):
    builder = InlineKeyboardBuilder()
    
    for prompt in prompts:
        builder.button(
            text=f"✏️ {prompt.name[:30]}", 
            callback_data=AdminCallback(action="update_prompt", prompt_id=prompt.id)
        )
        builder.button(
            text="❌", 
            callback_data=AdminCallback(action="delete_prompt", prompt_id=prompt.id)
        )
    
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data=AdminCallback(action="back").pack()))
    
    return builder.as_markup()
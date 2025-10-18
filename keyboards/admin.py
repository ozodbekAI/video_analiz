from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks.admin import AdminCallback
from typing import List, Optional
from database.models import Prompt

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data=AdminCallback(action="view_stats").pack()))
    builder.row(InlineKeyboardButton(text="👁 Просмотреть промпты", callback_data=AdminCallback(action="view_prompts").pack()))
    builder.row(InlineKeyboardButton(text="➕ Добавить промпт", callback_data=AdminCallback(action="add_prompt").pack()))
    builder.row(InlineKeyboardButton(text="👥 Топ пользователей", callback_data=AdminCallback(action="top_users").pack()))
    builder.row(InlineKeyboardButton(text="📹 Последние видео", callback_data=AdminCallback(action="recent_videos").pack()))
    return builder.as_markup()

def get_prompt_category_keyboard(add_mode: bool = False) -> InlineKeyboardMarkup:
    action_prefix = "add_select_category" if add_mode else "select_category"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📈 Анализ моего видео", callback_data=AdminCallback(action=action_prefix, category="my").pack()))
    builder.row(InlineKeyboardButton(text="🥊 Анализ конкурента", callback_data=AdminCallback(action=action_prefix, category="competitor").pack()))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallback(action="back").pack()))
    return builder.as_markup()

def get_prompt_type_keyboard(add_mode: bool = False) -> InlineKeyboardMarkup:
    action_prefix_type = "add_select_type" if add_mode else "select_type"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⛏️ Простой анализ (simple)", callback_data=AdminCallback(action=action_prefix_type, analysis_type="simple").pack()))
    builder.row(InlineKeyboardButton(text="⚙️ Расширенный анализ (advanced)", callback_data=AdminCallback(action=action_prefix_type, analysis_type="advanced").pack()))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallback(action="back").pack()))
    return builder.as_markup()

def get_advanced_subtype_keyboard(category: str = None, add_mode: bool = False) -> InlineKeyboardMarkup:
    action_prefix_subtype = "add_select_subtype" if add_mode else "select_subtype"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔝 Предыдущие промпты (advanced)", callback_data=AdminCallback(action=action_prefix_subtype, subtype="advanced").pack()))
    builder.row(InlineKeyboardButton(text="🔚 Финальный промпт (synthesis)", callback_data=AdminCallback(action=action_prefix_subtype, subtype="synthesis").pack()))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallback(action="back").pack()))
    return builder.as_markup()

def get_prompts_keyboard(prompts: Optional[List[Prompt]] = None, analysis_type: str = None, category: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if prompts:
        for prompt in prompts:
            builder.row(
                InlineKeyboardButton(text=f"🖊 Изменить {prompt.name}", callback_data=AdminCallback(action="update_prompt", prompt_id=prompt.id).pack()),
                InlineKeyboardButton(text=f"➖ Удалить {prompt.name}", callback_data=AdminCallback(action="delete_prompt", prompt_id=prompt.id).pack())
            )
    if analysis_type in ["advanced", "simple"]:
        builder.row(InlineKeyboardButton(text="➕ Добавить новый", callback_data=AdminCallback(action="add_prompt").pack()))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallback(action="back").pack()))
    return builder.as_markup()

def get_stats_keyboard() -> InlineKeyboardMarkup:
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data=AdminCallback(action="view_stats").pack()))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallback(action="back").pack()))
    return builder.as_markup()
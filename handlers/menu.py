from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from callbacks.menu import MenuCallback
from keyboards.client import get_strategic_hub_keyboard, get_main_menu_keyboard
from states.analysis import AnalysisFSM
from utils.texts import FEATURE_IN_DEVELOPMENT, STRATEGIC_HUB_TEXT
from utils.helpers import safe_edit_text

router = Router()


@router.callback_query(MenuCallback.filter(F.action == "strategic_hub"))
async def strategic_hub_handler(query: CallbackQuery):
    await safe_edit_text(
        query, 
        STRATEGIC_HUB_TEXT, 
        reply_markup=get_strategic_hub_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(MenuCallback.filter(F.action.in_({
    "content_evolution", 
    "audience_map", 
    "risk_monitoring", 
    "strengths", 
    "growth_plan", 
    "anomaly_detector",
    "motivation"
})))
async def in_development_handler(query: CallbackQuery):
    await query.answer(FEATURE_IN_DEVELOPMENT, show_alert=True)


@router.callback_query(MenuCallback.filter(F.action == "main_menu"))
async def main_menu_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(
        query,
        "Главное меню. Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
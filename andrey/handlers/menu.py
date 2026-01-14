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


# 🆕 Убираем ВСЕ заглушки - теперь все функции рабочие
@router.callback_query(MenuCallback.filter(F.action == "audience_map"))
async def audience_map_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="audience_map")


@router.callback_query(MenuCallback.filter(F.action == "content_prediction"))
async def content_prediction_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="content_prediction")


@router.callback_query(MenuCallback.filter(F.action == "channel_diagnostics"))
async def channel_diagnostics_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="channel_diagnostics")


@router.callback_query(MenuCallback.filter(F.action == "content_ideas"))
async def content_ideas_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="content_ideas")


@router.callback_query(MenuCallback.filter(F.action == "viral_potential"))
async def viral_potential_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="viral_potential")


@router.callback_query(MenuCallback.filter(F.action == "iterative_ideas"))
async def iterative_ideas_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.evolution import universal_analysis_handler
    await universal_analysis_handler(query, state, analysis_type="iterative_ideas")


@router.callback_query(MenuCallback.filter(F.action == "main_menu"))
async def main_menu_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(
        query,
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
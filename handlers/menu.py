from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from callbacks.menu import MenuCallback
from keyboards.client import get_analysis_type_keyboard
from states.analysis import AnalysisFSM
from utils.texts import ANALYSIS_COMPETITOR, ANALYSIS_MY_VIDEO, FEATURE_IN_DEVELOPMENT
from utils.helpers import safe_edit_text

router = Router()

@router.callback_query(MenuCallback.filter(F.action.in_({"health_index", "channel_dynamics", "content_generator", "crisis_manager", "personality_map", "trend_detector", "title_generator", "cover_generator", "strategy_planner", "monetization_monitor", "motivation"})))
async def in_development_handler(query: CallbackQuery):
    await query.answer(FEATURE_IN_DEVELOPMENT, show_alert=True)

@router.callback_query(MenuCallback.filter(F.action == "analysis_my_video"))
async def analysis_my_video_handler(query: CallbackQuery, state: FSMContext):
    # Use safe_edit_text instead of direct edit_text
    await safe_edit_text(query, ANALYSIS_MY_VIDEO, reply_markup=get_analysis_type_keyboard("my"))
    await state.set_state(AnalysisFSM.choose_type)

@router.callback_query(MenuCallback.filter(F.action == "analysis_competitor"))
async def analysis_competitor_handler(query: CallbackQuery, state: FSMContext):
    # Use safe_edit_text instead of direct edit_text
    await safe_edit_text(query, ANALYSIS_COMPETITOR, reply_markup=get_analysis_type_keyboard("competitor"))
    await state.set_state(AnalysisFSM.choose_type)
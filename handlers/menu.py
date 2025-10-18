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

# ❌ BU HANDLER'LARNI O'CHIRING! Ular analysis_handler.py da bor!
# @router.callback_query(MenuCallback.filter(F.action == "analysis_my_video"))
# async def analysis_my_video_handler(query: CallbackQuery, state: FSMContext):
#     await safe_edit_text(query, ANALYSIS_MY_VIDEO, reply_markup=get_analysis_type_keyboard("my"))
#     await state.set_state(AnalysisFSM.choose_type)

# @router.callback_query(MenuCallback.filter(F.action == "analysis_competitor"))
# async def analysis_competitor_handler(query: CallbackQuery, state: FSMContext):
#     await safe_edit_text(query, ANALYSIS_COMPETITOR, reply_markup=get_analysis_type_keyboard("competitor"))
#     await state.set_state(AnalysisFSM.choose_type)

# Yoki agar bu handler'lar kerak bo'lsa, to'g'rilang:

@router.callback_query(MenuCallback.filter(F.action == "analysis_my_video"))
async def analysis_my_video_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()  
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="my")  
    
    # DEBUG
    data = await state.get_data()
    print(f"DEBUG menu_handler.analysis_my_video: data = {data}")
    
    await safe_edit_text(query, ANALYSIS_MY_VIDEO, reply_markup=get_analysis_type_keyboard("my"))

@router.callback_query(MenuCallback.filter(F.action == "analysis_competitor"))
async def analysis_competitor_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AnalysisFSM.choose_type)
    await state.update_data(analysis_category="competitor") 
    
    # DEBUG
    data = await state.get_data()
    print(f"DEBUG menu_handler.analysis_competitor: data = {data}")
    
    await safe_edit_text(query, ANALYSIS_COMPETITOR, reply_markup=get_analysis_type_keyboard("competitor"))
from aiogram.fsm.state import State, StatesGroup


class AdminFSM(StatesGroup):
    # Prompts uchun
    waiting_for_category = State()
    waiting_for_type = State()
    waiting_for_subtype = State()
    waiting_for_prompt_name = State()
    waiting_for_prompt_text = State()
    waiting_for_update_text = State()
    
    # User management uchun
    waiting_for_user_id = State()
    managing_user = State()
    waiting_for_limit = State()
    
    # Sample reports uchun - YANGI
    waiting_for_sample_name = State()
    waiting_for_sample_url = State()
    waiting_for_sample_data = State()
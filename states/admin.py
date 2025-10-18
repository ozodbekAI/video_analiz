from aiogram.fsm.state import State, StatesGroup

class AdminFSM(StatesGroup):
    waiting_for_category = State()          
    waiting_for_type = State()              
    waiting_for_subtype = State()           
    waiting_for_prompt_name = State()       
    waiting_for_prompt_text = State()       
    waiting_for_update_text = State()       

from aiogram.fsm.state import State, StatesGroup

class AnalysisFSM(StatesGroup):
    choose_category = State() 
    choose_type = State()
    waiting_for_url = State()
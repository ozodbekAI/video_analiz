from aiogram.fsm.state import State, StatesGroup

class AnalysisFSM(StatesGroup):

    choose_type = State()
    waiting_for_url = State()

    waiting_for_shorts_url = State()
    choosing_shorts_level = State()

    processing = State()
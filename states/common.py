from aiogram.fsm.state import State, StatesGroup

class CommonFSM(StatesGroup):
    choosing_language = State()
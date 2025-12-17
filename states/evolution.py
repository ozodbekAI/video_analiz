from aiogram.fsm.state import StatesGroup, State


class EvolutionFSM(StatesGroup):
    selecting_channel = State()
    processing = State()
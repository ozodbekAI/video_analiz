from aiogram.fsm.state import State, StatesGroup


class EvolutionFSM(StatesGroup):
    selecting_channel = State()
    processing_evolution = State()
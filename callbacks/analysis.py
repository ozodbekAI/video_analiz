from aiogram.filters.callback_data import CallbackData

class AnalysisCallback(CallbackData, prefix="analysis"):
    type: str
    category: str
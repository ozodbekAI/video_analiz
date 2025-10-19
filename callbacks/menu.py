from aiogram.filters.callback_data import CallbackData
from typing import Optional

class MenuCallback(CallbackData, prefix="menu"):
    action: str
    category: Optional[str] = None  # til uchun
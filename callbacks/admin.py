from aiogram.filters.callback_data import CallbackData
from typing import Optional


class AdminCallback(CallbackData, prefix="admin"):
    action: str
    category: Optional[str] = None  
    analysis_type: Optional[str] = None  
    subtype: Optional[str] = None 
    prompt_id: Optional[int] = None
    sample_id: Optional[int] = None 
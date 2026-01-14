import asyncio
from aiogram.types import Message

SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]
PROGRESS_BAR_FULL = "▓"
PROGRESS_BAR_EMPTY = "░"


class ProgressTracker:
    
    def __init__(self, message: Message, total_steps: int = 100):
        self.message = message
        self.total_steps = total_steps
        self.current_step = 0
        self.spinner_index = 0
        self.status_message = None
        self.is_running = False
        self.animation_task = None
    
    async def start(self, initial_text: str = "Загрузка..."):
        self.is_running = True
        self.status_message = await self.message.answer(initial_text)
        
        self.animation_task = asyncio.create_task(self._animate())
    
    async def update(self, step: int, text: str = None):
        self.current_step = min(step, self.total_steps)
        
        if text:
            percentage = int((self.current_step / self.total_steps) * 100)
            progress_bar = self._get_progress_bar(percentage)
            
            full_text = f"{text}\n\n{progress_bar} {percentage}%"
            
            try:
                await self.status_message.edit_text(full_text)
            except Exception:
                pass  
    
    async def complete(self, text: str = "✅ Готово!"):
        self.is_running = False
        
        if self.animation_task:
            self.animation_task.cancel()
        
        try:
            await self.status_message.edit_text(text)
        except Exception:
            pass
    
    async def error(self, text: str = "❌ Ошибка"):
        self.is_running = False
        
        if self.animation_task:
            self.animation_task.cancel()
        
        try:
            await self.status_message.edit_text(text)
        except Exception:
            pass
    
    def _get_progress_bar(self, percentage: int) -> str:
        filled = percentage // 10
        empty = 10 - filled
        
        return PROGRESS_BAR_FULL * filled + PROGRESS_BAR_EMPTY * empty
    
    async def _animate(self):
        while self.is_running:
            try:
                spinner = SPINNER_FRAMES[self.spinner_index % len(SPINNER_FRAMES)]
                percentage = int((self.current_step / self.total_steps) * 100)
                progress_bar = self._get_progress_bar(percentage)
                
                text = f"{spinner} Обработка...\n\n{progress_bar} {percentage}%"
                
                await self.status_message.edit_text(text)
                self.spinner_index += 1
                
                await asyncio.sleep(0.5)  
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.5)


async def create_progress_tracker(message: Message, total_steps: int = 100) -> ProgressTracker:
    tracker = ProgressTracker(message, total_steps)
    return tracker
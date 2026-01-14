from aiogram import BaseMiddleware
from aiogram.types import Message
from config import Config
from typing import Callable, Dict, Any, Awaitable

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        config = Config()
        if event.from_user.id in config.ADMIN_IDS:
            data['is_admin'] = True
            print(f"Admin access granted to user ID: {event.from_user.id}")
        else:
            data['is_admin'] = False
        return await handler(event, data)
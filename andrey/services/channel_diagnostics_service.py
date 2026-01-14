from database.crud import get_user_analysis_history, get_prompts
from services.ai_service import analyze_comments_with_prompt


class ChannelDiagnosticsService:
    async def run(self, user_id: int) -> str:
        history = await get_user_analysis_history(user_id)
        if len(history) < 5:
            raise ValueError("NOT_ENOUGH_DATA")

        prompts = await get_prompts("channel_diagnostics")

        return await analyze_comments_with_prompt(
            "\n".join(history),
            prompts["main"]
        )


channel_diagnostics_service = ChannelDiagnosticsService()

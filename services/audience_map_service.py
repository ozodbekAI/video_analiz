from database.crud import get_user_analysis_history, get_prompts
from services.ai_service import analyze_comments_with_prompt


class AudienceMapService:
    async def run(self, user_id: int) -> str:
        history = await get_user_analysis_history(user_id)
        if len(history) < 3:
            raise ValueError("NOT_ENOUGH_DATA")

        prompts = await get_prompts("audience_map")

        return await analyze_comments_with_prompt(
            "\n".join(history),
            prompts["main"]
        )


audience_map_service = AudienceMapService()

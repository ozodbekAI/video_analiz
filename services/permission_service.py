from typing import List

# oddiy adminlar ro‘yxati (keyin DB ga o‘tkazamiz)
ADMIN_IDS = {
    7166331865,
    2119659554,  
}


class PermissionService:

    @staticmethod
    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS

    @staticmethod
    def check_access(user_id: int, feature: str) -> bool:
        """
        feature: iterative_ideas, strategic_hub, advanced_analysis, etc
        """
        if PermissionService.is_admin(user_id):
            return True

        # oddiy userlar uchun ruxsatlar
        allowed_features = {
            "iterative_ideas",
            "strategic_hub",
            "content_ideas",
        }

        return feature in allowed_features

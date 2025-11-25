import secrets
import string
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, update
from database.engine import async_session
from database.models import User, VerificationAttempt
import re


class VerificationService:
    
    @staticmethod
    def generate_verification_code() -> str:
        chars = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(chars) for _ in range(8))
        return f"YT-PULSE-VERIFY-{code}"
    
    @staticmethod
    async def cancel_pending_verification(user_id: int) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return
            
            await session.execute(
                update(VerificationAttempt)
                .where(VerificationAttempt.user_id == user.id)
                .where(VerificationAttempt.status == 'pending')
                .values(status='cancelled')
            )
            
            await session.commit()
    
    @staticmethod
    async def initiate_verification(user_id: int, channel_url: str) -> Tuple[str, int]:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError("Foydalanuvchi topilmadi")
            
            await session.execute(
                update(VerificationAttempt)
                .where(VerificationAttempt.user_id == user.id)
                .where(VerificationAttempt.status == 'pending')
                .values(status='cancelled')
            )
            
            verification_code = VerificationService.generate_verification_code()
            
            attempt = VerificationAttempt(
                user_id=user.id,
                channel_url=channel_url,
                verification_code=verification_code,
                verification_method='code',
                status='pending',
                created_at=datetime.now(tz=timezone.utc)
            )
            
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)
            
            return verification_code, attempt.id
    
    @staticmethod
    def normalize_channel_url(channel_url: str) -> str:
        patterns = [
            (r'youtube\.com/@([^/?]+)', lambda m: f"@{m.group(1)}"),
            (r'youtube\.com/channel/([^/?]+)', lambda m: m.group(1)),
            (r'youtube\.com/c/([^/?]+)', lambda m: m.group(1)),
            (r'youtube\.com/user/([^/?]+)', lambda m: m.group(1))
        ]
        
        for pattern, extractor in patterns:
            match = re.search(pattern, channel_url)
            if match:
                return extractor(match)
        
        return channel_url
    
    @staticmethod
    def extract_channel_id_from_url(channel_url: str) -> Optional[str]:
        patterns = [
            r"youtube\.com/@([^/?]+)",
            r"youtube\.com/channel/([^/?]+)",
            r"youtube\.com/c/([^/?]+)",
            r"youtube\.com/user/([^/?]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    async def check_code_in_description(
        attempt_id: int,
        channel_description: str
    ) -> Tuple[bool, str]:
        async with async_session() as session:
            result = await session.execute(
                select(VerificationAttempt).where(VerificationAttempt.id == attempt_id)
            )
            attempt = result.scalar_one_or_none()
            
            if not attempt:
                return False, "Verifikatsiya urinishi topilmadi"
            
            if attempt.status == 'verified':
                return False, "Bu kanal allaqachon tekshirilgan"
            
            if attempt.status != 'pending':
                return False, "Verifikatsiya bekor qilingan yoki yaroqsiz"
              
            if attempt.verification_code in channel_description:
                stmt = update(VerificationAttempt).where(
                    VerificationAttempt.id == attempt_id
                ).values(
                    status='verified',
                    verified_at=datetime.now(tz=timezone.utc)
                )
                await session.execute(stmt)
                
                user_stmt = update(User).where(
                    User.id == attempt.user_id
                ).values(
                    youtube_channel_id=attempt.channel_url,
                    verification_method='code',
                    verification_status='verified',
                    verification_date=datetime.now(tz=timezone.utc)
                )
                await session.execute(user_stmt)
                
                await session.commit()
                
                return True, "Kanal muvaffaqiyatli tasdiqlandi!"
            else:
                stmt = update(VerificationAttempt).where(
                    VerificationAttempt.id == attempt_id
                ).values(
                    attempts=attempt.attempts + 1
                )
                await session.execute(stmt)
                await session.commit()
                
                return False, "Код kanal tavsifida topilmadi. Iltimos, kodni to'g'ri joylashtirganingizga ishonch hosil qiling."
    
    @staticmethod
    async def verify_with_oauth(
        user_id: int,
        channel_id: str,
        channel_title: str
    ) -> Tuple[bool, str]:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "Foydalanuvchi topilmadi"
            
            stmt = update(User).where(User.user_id == user_id).values(
                youtube_channel_id=channel_id,
                verification_method='oauth',
                verification_status='verified',
                verification_date=datetime.now(tz=timezone.utc)
            )
            await session.execute(stmt)

            attempt = VerificationAttempt(
                user_id=user.id,
                channel_url=f"https://www.youtube.com/channel/{channel_id}",
                verification_code="OAUTH",
                verification_method='oauth',
                status='verified',
                verified_at=datetime.now(tz=timezone.utc),
                created_at=datetime.now(tz=timezone.utc)
            )
            session.add(attempt)
            
            await session.commit()
            
            return True, f"Kanal '{channel_title}' muvaffaqiyatli tasdiqlandi!"
    
    @staticmethod
    async def get_user_verification_status(user_id: int) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    'is_verified': False,
                    'channel_id': None,
                    'verification_method': None,
                    'verification_date': None
                }
            
            return {
                'is_verified': user.verification_status == 'verified',
                'channel_id': user.youtube_channel_id,
                'verification_method': user.verification_method,
                'verification_date': user.verification_date
            }
    
    @staticmethod
    async def check_access_permission(
        user_id: int,
        required_feature: str
    ) -> Tuple[bool, str]:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "Foydalanuvchi topilmadi"
            
            feature_requirements = {
                'simple_analysis': ['starter', 'pro', 'business', 'enterprise'],
                'advanced_analysis': ['pro', 'business', 'enterprise'],
                'strategic_hub': ['business', 'enterprise'],
                'emotional_dna': ['enterprise'],
                'what_if': ['enterprise']
            }
            
            allowed_tariffs = feature_requirements.get(required_feature, [])
            
            if user.tariff_plan not in allowed_tariffs:
                if user.tariff_plan == 'starter':
                    return False, "Bu funksiya faqat to'lovli tariflarda mavjud. Tarifni yangilang!"
                else:
                    return False, f"Bu funksiya faqat {', '.join(allowed_tariffs)} tariflarida mavjud."
            
            return True, "Ruxsat berildi"
    
    @staticmethod
    async def get_pending_verification(user_id: int) -> Optional[dict]:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            attempt_result = await session.execute(
                select(VerificationAttempt)
                .where(VerificationAttempt.user_id == user.id)
                .where(VerificationAttempt.status == 'pending')
                .order_by(VerificationAttempt.created_at.desc())
                .limit(1)  # Faqat bitta
            )
            attempt = attempt_result.scalar_one_or_none()
            
            if not attempt:
                return None
            
            return {
                'id': attempt.id,
                'code': attempt.verification_code,
                'channel_url': attempt.channel_url,
                'created_at': attempt.created_at
            }
    
    @staticmethod
    async def is_channel_verified(user_id: int, video_channel_url: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or user.verification_status != 'verified':
                return False

            user_channel_normalized = VerificationService.normalize_channel_url(user.youtube_channel_id)
            video_channel_normalized = VerificationService.normalize_channel_url(video_channel_url)
            
            return user_channel_normalized == video_channel_normalized
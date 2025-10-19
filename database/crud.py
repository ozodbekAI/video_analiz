from sqlalchemy import select, insert, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Video, Comment, Prompt, AIResponse
from .engine import async_session
from datetime import datetime, timezone, timedelta


async def get_user(user_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        
        # Oylik reset tekshirish
        if user:
            await check_and_reset_monthly_limit(user, session)
        
        return user


async def check_and_reset_monthly_limit(user: User, session: AsyncSession):
    """Har oyda limitni reset qilish"""
    now = datetime.now(tz=timezone.utc)
    
    if user.last_reset_date:
        days_passed = (now - user.last_reset_date).days
        
        if days_passed >= 30:
            stmt = update(User).where(User.id == user.id).values(
                analyses_used=0,
                last_reset_date=now
            )
            await session.execute(stmt)
            await session.commit()
            user.analyses_used = 0
            user.last_reset_date = now


async def create_user(user_id: int, username: str):
    async with async_session() as session:
        stmt = insert(User).values(
            user_id=user_id,
            username=username,
            language="ru",
            analyses_limit=5,
            analyses_used=0,
            last_reset_date=datetime.now(tz=timezone.utc),
            created_at=datetime.now(tz=timezone.utc)
        )
        await session.execute(stmt)
        await session.commit()


async def update_user_language(user_id: int, language: str):
    """Foydalanuvchi tilini yangilash"""
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(language=language)
        await session.execute(stmt)
        await session.commit()


async def update_user_analyses(user_id: int, used: int):
    """So'rovlar sonini yangilash"""
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(analyses_used=used)
        await session.execute(stmt)
        await session.commit()


async def set_user_limit(user_id: int, new_limit: int):
    """ADMIN: Foydalanuvchi limitini o'zgartirish"""
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(analyses_limit=new_limit)
        await session.execute(stmt)
        await session.commit()


async def reset_user_analyses(user_id: int):
    """ADMIN: Foydalanuvchi so'rovlarini 0 ga qaytarish"""
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(
            analyses_used=0,
            last_reset_date=datetime.now(tz=timezone.utc)
        )
        await session.execute(stmt)
        await session.commit()


async def get_prompts(category: str = None, analysis_type: str = None):
    async with async_session() as session:
        query = select(Prompt)
        if category:
            query = query.where(Prompt.category == category)
        if analysis_type:
            query = query.where(Prompt.analysis_type == analysis_type)
        result = await session.execute(query)
        return result.scalars().all()


async def create_prompt(name: str, prompt_text: str, analysis_type: str = None, category: str = None):
    async with async_session() as session:
        stmt = insert(Prompt).values(name=name, prompt_text=prompt_text, analysis_type=analysis_type, category=category)
        await session.execute(stmt)
        await session.commit()


async def update_prompt(prompt_id: int, prompt_text: str):
    async with async_session() as session:
        stmt = update(Prompt).where(Prompt.id == prompt_id).values(prompt_text=prompt_text)
        await session.execute(stmt)
        await session.commit()


async def delete_prompt(prompt_id: int):
    async with async_session() as session:
        stmt = delete(Prompt).where(Prompt.id == prompt_id)
        await session.execute(stmt)
        await session.commit()


async def create_video(user_id: int, video_url: str, video_title: str):
    async with async_session() as session:
        stmt = insert(Video).values(
            user_id=user_id,
            video_url=video_url,
            video_title=video_title,
            processed_at=datetime.now(tz=timezone.utc)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.inserted_primary_key[0]


async def create_comments(video_id: int, comments: list):
    async with async_session() as session:
        for idx, comment in enumerate(comments):
            timestamp_str = comment['time'].strip()
            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            stmt = insert(Comment).values(
                video_id=video_id,
                raw_text=comment['text'],
                timestamp=timestamp,
                chunk_id=idx // 100
            )
            await session.execute(stmt)
        await session.commit()


async def get_comments(video_id: int):
    async with async_session() as session:
        result = await session.execute(select(Comment).where(Comment.video_id == video_id))
        return result.scalars().all()


async def create_ai_response(user_id: int, video_id: int, chunk_id: int, analysis_type: str, response_text: str):
    async with async_session() as session:
        stmt = insert(AIResponse).values(
            user_id=user_id,
            video_id=video_id,
            chunk_id=chunk_id,
            analysis_type=analysis_type,
            response_text=response_text,
            created_at=datetime.now(tz=timezone.utc)
        )
        await session.execute(stmt)
        await session.commit()


# STATISTIKA FUNKSIYALARI

async def get_total_users():
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def get_total_videos():
    async with async_session() as session:
        result = await session.execute(select(func.count(Video.id)))
        return result.scalar() or 0


async def get_total_ai_requests():
    async with async_session() as session:
        result = await session.execute(select(func.count(AIResponse.id)))
        return result.scalar() or 0


async def get_users_today():
    async with async_session() as session:
        today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
        return result.scalar() or 0


async def get_videos_today():
    async with async_session() as session:
        today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(Video.id)).where(Video.processed_at >= today_start)
        )
        return result.scalar() or 0


async def get_ai_requests_today():
    async with async_session() as session:
        today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(AIResponse.id)).where(AIResponse.created_at >= today_start)
        )
        return result.scalar() or 0


async def get_analysis_type_stats():
    async with async_session() as session:
        result = await session.execute(
            select(
                AIResponse.analysis_type,
                func.count(AIResponse.id).label('count')
            ).group_by(AIResponse.analysis_type)
        )
        return dict(result.all())


async def get_top_active_users(limit: int = 5):
    async with async_session() as session:
        result = await session.execute(
            select(
                User.user_id,
                User.username,
                func.count(Video.id).label('video_count')
            )
            .join(Video, Video.user_id == User.id)
            .group_by(User.id)
            .order_by(desc('video_count'))
            .limit(limit)
        )
        return result.all()


async def get_recent_videos(limit: int = 5):
    async with async_session() as session:
        result = await session.execute(
            select(Video, User.username)
            .join(User, User.id == Video.user_id)
            .order_by(desc(Video.processed_at))
            .limit(limit)
        )
        return result.all()


async def get_average_comments_per_video():
    async with async_session() as session:
        subquery = (
            select(
                Comment.video_id,
                func.count(Comment.id).label('comment_count')
            )
            .group_by(Comment.video_id)
            .subquery()
        )
        
        result = await session.execute(
            select(func.avg(subquery.c.comment_count))
        )
        avg = result.scalar()
        return round(avg, 1) if avg else 0


async def get_prompts_count():
    async with async_session() as session:
        result = await session.execute(select(func.count(Prompt.id)))
        return result.scalar() or 0


async def get_user_videos_history(user_id: int, limit: int = 10, offset: int = 0):
    async with async_session() as session:
        user_result = await session.execute(
            select(User.id).where(User.user_id == user_id)
        )
        db_user_id = user_result.scalar_one_or_none()
        
        if not db_user_id:
            return [], 0
        
        count_result = await session.execute(
            select(func.count(Video.id)).where(Video.user_id == db_user_id)
        )
        total_count = count_result.scalar() or 0
        
        result = await session.execute(
            select(Video, AIResponse)
            .outerjoin(AIResponse, AIResponse.video_id == Video.id)
            .where(Video.user_id == db_user_id)
            .where(AIResponse.chunk_id == 0)
            .order_by(desc(Video.processed_at))
            .limit(limit)
            .offset(offset)
        )
        
        videos = result.all()
        return videos, total_count


async def get_video_by_id(video_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Video).where(Video.id == video_id)
        )
        return result.scalar_one_or_none()


async def get_ai_response_by_video(video_id: int, analysis_type: str = None):
    async with async_session() as session:
        query = select(AIResponse).where(
            AIResponse.video_id == video_id,
            AIResponse.chunk_id == 0
        )
        if analysis_type:
            query = query.where(AIResponse.analysis_type == analysis_type)
        
        result = await session.execute(query.order_by(desc(AIResponse.created_at)))
        return result.scalar_one_or_none()


async def get_user_by_id(user_id: int):
    """User ID orqali foydalanuvchi ma'lumotlarini olish"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
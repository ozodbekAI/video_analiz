from sqlalchemy import select, insert, update, delete, func, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from .models import (
    EvolutionAnalysis,
    User,
    Video,
    Comment,
    Prompt,
    AIResponse,
    VerificationAttempt,
    VideoAnalysis,
    VideoAnalysisSet,
    AnalysisQualityMarker,
    MultiAnalysisPrompt,
)
from .engine import async_session
from datetime import datetime, timezone, timedelta


async def _resolve_user(session: AsyncSession, user_identifier: int) -> User:
    """
    Resolves a user by either Telegram user_id (User.user_id) or internal DB id (User.id).
    If not found, creates a minimal user record using the provided identifier as Telegram user_id.
    
    This helper is intentionally defensive because the codebase mixes identifiers.
    """
    # 1) Try Telegram user id
    res = await session.execute(select(User).where(User.user_id == user_identifier))
    user = res.scalar_one_or_none()
    if user:
        return user

    # 2) Try internal DB id
    res = await session.execute(select(User).where(User.id == user_identifier))
    user = res.scalar_one_or_none()
    if user:
        return user

    # 3) Create new user (best-effort)
    user = User(
        user_id=user_identifier,
        username=f"user_{user_identifier}",
        language="ru",
        tariff_plan="free",
        analyses_limit=5,
        analyses_used=0,
        last_reset_date=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )
    session.add(user)
    await session.flush()
    return user


async def get_user(user_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user:
            await check_and_reset_monthly_limit(user, session)
        
        return user


async def check_and_reset_monthly_limit(user: User, session: AsyncSession):
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
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(language=language)
        await session.execute(stmt)
        await session.commit()


async def update_user_analyses(user_id: int, used: int):
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(analyses_used=used)
        await session.execute(stmt)
        await session.commit()


async def set_user_limit(user_id: int, new_limit: int):
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(analyses_limit=new_limit)
        await session.execute(stmt)
        await session.commit()


async def reset_user_analyses(user_id: int):
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(
            analyses_used=0,
            last_reset_date=datetime.now(tz=timezone.utc)
        )
        await session.execute(stmt)
        await session.commit()


async def get_prompts(
    category: str | None = None,
    analysis_type: str | None = None,
):
    async with async_session() as db:
        query = select(Prompt)
        if category:
            query = query.where(Prompt.category == category)
        if analysis_type:
            query = query.where(Prompt.analysis_type == analysis_type)

        res = await db.execute(query.order_by(Prompt.order))
        return res.scalars().all()


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
    """Create Video row.

    NOTE: `user_id` may be either Telegram user_id or internal DB id; we resolve defensively.
    """
    async with async_session() as session:
        user = await _resolve_user(session, user_id)

        stmt = insert(Video).values(
            user_id=user.id,
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


async def create_ai_response(
    user_id: int,
    video_id: int,
    chunk_id: int,
    analysis_type: str,
    response_text: str,
    machine_data: str | None = None,
):
    """Store an AI response.

    IMPORTANT: The codebase historically mixes Telegram user_id and internal DB user.id.
    This function resolves either form and always stores internal user.id in AIResponse.user_id.
    """
    async with async_session() as session:
        user = await _resolve_user(session, user_id)

        stmt = (
            insert(AIResponse)
            .values(
                user_id=user.id,
                video_id=video_id,
                chunk_id=chunk_id,
                analysis_type=analysis_type,
                response_text=response_text,
                machine_data=machine_data,
                created_at=datetime.now(tz=timezone.utc),
            )
            .returning(AIResponse.id)
        )
        res = await session.execute(stmt)
        await session.commit()
        return int(res.scalar_one())


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
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_user_with_verification(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            await check_and_reset_monthly_limit(user, session)
        
        return user


async def update_user_verification(
    user_id: int,
    channel_id: str,
    method: str,
    status: str = 'verified'
):
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(
            youtube_channel_id=channel_id,
            verification_method=method,
            verification_status=status,
            verification_date=datetime.now(tz=timezone.utc) if status == 'verified' else None
        )
        await session.execute(stmt)
        await session.commit()


async def create_verification_attempt(
    user_id: int,
    channel_url: str,
    verification_code: str,
    method: str = 'code'
):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            raise ValueError("Foydalanuvchi topilmadi")
        
        attempt = VerificationAttempt(
            user_id=user.id,
            channel_url=channel_url,
            verification_code=verification_code,
            verification_method=method,
            status='pending',
            created_at=datetime.now(tz=timezone.utc)
        )
        
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        
        return attempt.id


async def get_verification_attempt(attempt_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(VerificationAttempt).where(VerificationAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()


async def update_verification_attempt_status(
    attempt_id: int,
    status: str,
    verified: bool = False
):
    async with async_session() as session:
        values = {'status': status}
        
        if verified:
            values['verified_at'] = datetime.now(tz=timezone.utc)
        else:
            attempt_result = await session.execute(
                select(VerificationAttempt).where(VerificationAttempt.id == attempt_id)
            )
            attempt = attempt_result.scalar_one_or_none()
            if attempt:
                values['attempts'] = attempt.attempts + 1
        
        stmt = update(VerificationAttempt).where(
            VerificationAttempt.id == attempt_id
        ).values(**values)
        
        await session.execute(stmt)
        await session.commit()


async def get_latest_verification_attempt(user_id: int):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return None
        
        result = await session.execute(
            select(VerificationAttempt)
            .where(VerificationAttempt.user_id == user.id)
            .where(VerificationAttempt.status == 'pending')
            .order_by(VerificationAttempt.created_at.desc())
        )
        return result.scalar_one_or_none()


async def check_user_tariff_access(user_id: int, feature: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        feature_tariffs = {
            'simple': ['starter', 'pro', 'business', 'enterprise'],
            'advanced': ['pro', 'business', 'enterprise'],
            'strategic_hub': ['business', 'enterprise'],
            'emotional_dna': ['enterprise'],
            'what_if': ['enterprise']
        }
        
        allowed = feature_tariffs.get(feature, [])
        return user.tariff_plan in allowed


async def get_user_verification_stats(user_id: int) -> dict:
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return {
                'total_attempts': 0,
                'verified': False,
                'pending_attempts': 0
            }
        
        total_result = await session.execute(
            select(func.count(VerificationAttempt.id))
            .where(VerificationAttempt.user_id == user.id)
        )
        total_attempts = total_result.scalar() or 0
        
        pending_result = await session.execute(
            select(func.count(VerificationAttempt.id))
            .where(VerificationAttempt.user_id == user.id)
            .where(VerificationAttempt.status == 'pending')
        )
        pending_attempts = pending_result.scalar() or 0
        
        return {
            'total_attempts': total_attempts,
            'verified': user.verification_status == 'verified',
            'pending_attempts': pending_attempts,
            'channel_id': user.youtube_channel_id,
            'verification_date': user.verification_date
        }


async def update_ai_response_txt_path(user_id: int, video_id: int, txt_path: str):
    async with async_session() as session:
        stmt = update(AIResponse).where(
            AIResponse.user_id == user_id,
            AIResponse.video_id == video_id,
            AIResponse.analysis_type.in_(['simple', 'advanced', 'advanced_final'])
        ).values(txt_file_path=txt_path)
        
        await session.execute(stmt)
        await session.commit()


# =========================
# TZ-2: Multi-analysis optimizer helpers (Advanced-only)
# =========================


async def update_ai_response_files_by_id(
    ai_response_id: int,
    *,
    txt_path: str | None = None,
    pdf_path: str | None = None,
    machine_data: str | dict | None = None,
    analysis_set_id: int | None = None,
    is_for_strategic_hub: bool | None = None,
):
    """Update file paths / flags for a specific AIResponse by id."""
    values: dict = {}
    if txt_path is not None:
        values["txt_file_path"] = txt_path
    if pdf_path is not None:
        values["pdf_file_path"] = pdf_path
    if analysis_set_id is not None:
        values["analysis_set_id"] = analysis_set_id
    if is_for_strategic_hub is not None:
        values["is_for_strategic_hub"] = is_for_strategic_hub

    if machine_data is not None:
        # Keep JSON column type: accept dict or JSON string
        import json

        if isinstance(machine_data, str):
            try:
                values["machine_data"] = json.loads(machine_data)
            except Exception:
                values["machine_data"] = machine_data
        else:
            values["machine_data"] = machine_data

    if not values:
        return

    async with async_session() as session:
        stmt = update(AIResponse).where(AIResponse.id == ai_response_id).values(**values)
        await session.execute(stmt)
        await session.commit()


async def get_active_multi_analysis_prompt() -> MultiAnalysisPrompt | None:
    """Return active evaluator prompt (TZ-2)."""
    async with async_session() as session:
        res = await session.execute(
            select(MultiAnalysisPrompt)
            .where(MultiAnalysisPrompt.is_active == True)  # noqa: E712
            .order_by(MultiAnalysisPrompt.updated_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()


async def register_advanced_analysis_to_set(
    *,
    user_identifier: int,
    youtube_video_id: str,
    db_video_id: int | None,
    ai_response_id: int,
):
    """Attach an advanced final analysis (AIResponse) to a VideoAnalysisSet.

    - Creates set on first analysis.
    - Updates last_analysis_at and schedules next_evaluation_at = now + 24h.
    - Increments total_analyses.
    """
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        user = await _resolve_user(session, user_identifier)

        res = await session.execute(
            select(VideoAnalysisSet)
            .where(VideoAnalysisSet.user_id == user.id)
            .where(VideoAnalysisSet.video_id == youtube_video_id)
            .limit(1)
        )
        analysis_set = res.scalar_one_or_none()

        if not analysis_set:
            analysis_set = VideoAnalysisSet(
                user_id=user.id,
                video_id=youtube_video_id,
                db_video_id=db_video_id,
                total_analyses=0,
                status="collecting",
                created_at=now,
            )
            session.add(analysis_set)
            await session.flush()

        # Increment and schedule
        analysis_set.total_analyses = int(analysis_set.total_analyses or 0) + 1
        analysis_set.last_analysis_at = now
        analysis_set.next_evaluation_at = now + timedelta(hours=24)
        analysis_set.status = "waiting" if analysis_set.total_analyses >= 3 else "collecting"

        # Link AIResponse
        await session.execute(
            update(AIResponse)
            .where(AIResponse.id == ai_response_id)
            .values(analysis_set_id=analysis_set.id)
        )

        await session.commit()
        return analysis_set.id


async def get_due_video_analysis_sets(limit: int = 25) -> list[VideoAnalysisSet]:
    """Return sets eligible for evaluation now."""
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        res = await session.execute(
            select(VideoAnalysisSet)
            .where(VideoAnalysisSet.total_analyses >= 3)
            .where(VideoAnalysisSet.next_evaluation_at.isnot(None))
            .where(VideoAnalysisSet.next_evaluation_at <= now)
            .where(VideoAnalysisSet.status.in_(["waiting", "collecting", "error"]))
            .order_by(VideoAnalysisSet.next_evaluation_at.asc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def get_final_advanced_analyses_for_set(analysis_set_id: int) -> list[AIResponse]:
    """Fetch final advanced analyses (chunk_id=0, analysis_type='advanced') for a set."""
    async with async_session() as session:
        res = await session.execute(
            select(AIResponse)
            .where(AIResponse.analysis_set_id == analysis_set_id)
            .where(AIResponse.chunk_id == 0)
            .where(AIResponse.analysis_type.in_(["advanced", "advanced_final"]))
            .order_by(AIResponse.created_at.asc())
        )
        return list(res.scalars().all())


async def save_multi_analysis_evaluation(
    *,
    analysis_set_id: int,
    best_analysis_id: int,
    evaluation_result: dict,
    evaluations: list[dict],
):
    """Persist evaluator output and quality markers; returns nothing."""
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        # Update set
        await session.execute(
            update(VideoAnalysisSet)
            .where(VideoAnalysisSet.id == analysis_set_id)
            .values(
                best_analysis_id=best_analysis_id,
                evaluation_result=evaluation_result,
                evaluated_at=now,
                status="completed",
                evaluation_count=VideoAnalysisSet.evaluation_count + 1,
            )
        )

        # Reset strategic hub flags for this set
        await session.execute(
            update(AIResponse)
            .where(AIResponse.analysis_set_id == analysis_set_id)
            .values(is_for_strategic_hub=False)
        )
        await session.execute(
            update(AIResponse)
            .where(AIResponse.id == best_analysis_id)
            .values(is_for_strategic_hub=True)
        )

        # Upsert markers
        for ev in evaluations:
            analysis_id = int(ev.get("analysis_id"))
            res = await session.execute(
                select(AnalysisQualityMarker)
                .where(AnalysisQualityMarker.analysis_set_id == analysis_set_id)
                .where(AnalysisQualityMarker.analysis_id == analysis_id)
                .limit(1)
            )
            marker = res.scalar_one_or_none()

            values = dict(
                quality_rank=ev.get("quality_rank"),
                is_best=(analysis_id == best_analysis_id),
                total_score=ev.get("total_score"),
                scores=ev.get("scores"),
                strengths=ev.get("strengths"),
                weaknesses=ev.get("weaknesses"),
                improvement_suggestions=ev.get("improvement_suggestions"),
                updated_at=now,
            )

            if marker:
                await session.execute(
                    update(AnalysisQualityMarker)
                    .where(AnalysisQualityMarker.id == marker.id)
                    .values(**values)
                )
            else:
                marker = AnalysisQualityMarker(
                    analysis_set_id=analysis_set_id,
                    analysis_id=analysis_id,
                    created_at=now,
                    **values,
                )
                session.add(marker)

        await session.commit()


async def mark_pdf_deleted_for_analysis(analysis_set_id: int, analysis_id: int):
    """Mark PDF deleted in marker table (best-effort)."""
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        await session.execute(
            update(AnalysisQualityMarker)
            .where(AnalysisQualityMarker.analysis_set_id == analysis_set_id)
            .where(AnalysisQualityMarker.analysis_id == analysis_id)
            .values(pdf_deleted=True, pdf_deleted_at=now, updated_at=now)
        )
        await session.commit()


async def update_video_channel_id(video_id: int, channel_id: str):
    async with async_session() as session:
        stmt = update(Video).where(Video.id == video_id).values(channel_id=channel_id)
        await session.execute(stmt)
        await session.commit()


async def get_user_verified_channels_with_names(user_id: int):

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return []
        
        stmt = select(Video.channel_id, func.count(Video.id).label('video_count')).where(
            Video.user_id == user.id,
            Video.channel_id.isnot(None)
        ).group_by(Video.channel_id)
        
        result = await session.execute(stmt)
        channels = result.all()
        
        verified_attempts = await session.execute(
            select(VerificationAttempt.channel_url).where(
                VerificationAttempt.user_id == user.id,
                VerificationAttempt.status == 'verified'
            )
        )
        
        import re
        verified_channel_ids = set()
        for (channel_url,) in verified_attempts.all():
            match = re.search(r'channel/([^/?]+)', channel_url)
            if match:
                verified_channel_ids.add(match.group(1))
            match = re.search(r'@([^/?]+)', channel_url)
            if match:
                verified_channel_ids.add(match.group(1))
        
        channels_with_names = []
        processed_ids = set()
        
        for channel_id, video_count in channels:
            if channel_id not in processed_ids:
                processed_ids.add(channel_id)
                
                try:
                    from services.youtube_service import get_channel_info_by_id
                    channel_info = await get_channel_info_by_id(channel_id)
                    channel_title = channel_info.get('title', channel_id[:20])
                except Exception:
                    channel_title = channel_id[:20] + "..."
                
                channels_with_names.append({
                    'channel_id': channel_id,
                    'channel_title': channel_title,
                    'video_count': video_count
                })
        
        for channel_id in verified_channel_ids:
            if channel_id not in processed_ids:
                processed_ids.add(channel_id)
                
                count_result = await session.execute(
                    select(func.count(Video.id)).where(
                        Video.user_id == user.id,
                        Video.channel_id == channel_id
                    )
                )
                video_count = count_result.scalar() or 0
                
                try:
                    from services.youtube_service import get_channel_info_by_id
                    channel_info = await get_channel_info_by_id(channel_id)
                    channel_title = channel_info.get('title', channel_id[:20])
                except Exception:
                    channel_title = channel_id[:20] + "..."
                
                channels_with_names.append({
                    'channel_id': channel_id,
                    'channel_title': channel_title,
                    'video_count': video_count
                })
        
        return channels_with_names


async def get_channel_analysis_history(user_id: int, channel_id: str, limit: int = 10):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return []
        
        stmt = select(Video, AIResponse).join(
            AIResponse, Video.id == AIResponse.video_id
        ).where(
            Video.user_id == user.id,
            Video.channel_id == channel_id,
            AIResponse.txt_file_path.isnot(None),
            AIResponse.analysis_type == 'advanced'
        ).order_by(Video.processed_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        history = result.all()
        
        return [
            {
                'video_id': video.id,
                'video_url': video.video_url,
                'processed_at': video.processed_at,
                'txt_path': ai_response.txt_file_path,
                'analysis_type': ai_response.analysis_type
            }
            for video, ai_response in history
        ]



async def create_admin_verified_channel(user_id: int, channel_id: str, channel_title: str):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        existing_attempt = await session.execute(
            select(VerificationAttempt).where(
                VerificationAttempt.user_id == user.id,
                VerificationAttempt.channel_url.contains(channel_id),
                VerificationAttempt.status == 'verified'
            )
        )
        
        if existing_attempt.scalar_one_or_none():
            return
        
        attempt = VerificationAttempt(
            user_id=user.id,
            channel_url=f"https://www.youtube.com/channel/{channel_id}",
            verification_code="ADMIN_VERIFIED",
            verification_method='code',
            status='verified',
            verified_at=datetime.now(tz=timezone.utc),
            created_at=datetime.now(tz=timezone.utc)
        )
        
        session.add(attempt)
        await session.commit()



async def create_evolution_analysis(
    user_id: int,
    channel_id: str,
    channel_title: str = None,
    videos_analyzed: int = 0,
    video_ids_used: list = None
):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            raise ValueError("Foydalanuvchi topilmadi")
        
        evolution = EvolutionAnalysis(
            user_id=user.id,
            channel_id=channel_id,
            channel_title=channel_title,
            videos_analyzed=videos_analyzed,
            video_ids_used=video_ids_used or [],
            status='processing',
            created_at=datetime.now(tz=timezone.utc)
        )
        
        session.add(evolution)
        await session.commit()
        await session.refresh(evolution)
        
        return evolution


async def update_evolution_step1(evolution_id: int, response_text: str):
    async with async_session() as session:
        stmt = update(EvolutionAnalysis).where(
            EvolutionAnalysis.id == evolution_id
        ).values(step1_response=response_text)
        
        await session.execute(stmt)
        await session.commit()


async def update_evolution_step2(
    evolution_id: int,
    response_text: str,
    pdf_path: str = None,
    txt_path: str = None,
    analysis_period: str = None
):
    async with async_session() as session:
        values = {
            'step2_response': response_text,
            'status': 'completed',
            'completed_at': datetime.now(tz=timezone.utc)
        }
        
        if pdf_path:
            values['pdf_path'] = pdf_path
        if txt_path:
            values['txt_path'] = txt_path
        if analysis_period:
            values['analysis_period'] = analysis_period
        
        stmt = update(EvolutionAnalysis).where(
            EvolutionAnalysis.id == evolution_id
        ).values(**values)
        
        await session.execute(stmt)
        await session.commit()


async def get_user_evolution_history(user_id: int, limit: int = 10):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return []
        
        stmt = select(EvolutionAnalysis).where(
            EvolutionAnalysis.user_id == user.id,
            EvolutionAnalysis.status == 'completed'
        ).order_by(EvolutionAnalysis.completed_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_channel_latest_evolution(user_id: int, channel_id: str):
    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return None
        
        stmt = select(EvolutionAnalysis).where(
            EvolutionAnalysis.user_id == user.id,
            EvolutionAnalysis.channel_id == channel_id,
            EvolutionAnalysis.status == 'completed'
        ).order_by(EvolutionAnalysis.completed_at.desc()).limit(1)
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    

async def get_balanced_evolution_analyses(
    user_id: int, 
    channel_id: str, 
    min_advanced: int = 5, 
    total_limit: int = 10
):

    async with async_session() as session:

        user = await _resolve_user(session, user_id)
        
        if not user:
            return []
        
        advanced_stmt = select(Video, AIResponse).join(
            AIResponse, Video.id == AIResponse.video_id
        ).where(
            Video.user_id == user.id,
            Video.channel_id == channel_id,
            AIResponse.txt_file_path.isnot(None),
            AIResponse.chunk_id == 0,
            AIResponse.analysis_type.in_(['advanced', 'advanced_final']),
            Video.processed_at.isnot(None)  
        ).order_by(Video.processed_at.asc())

        advanced_result = await session.execute(advanced_stmt)
        advanced_analyses = advanced_result.all()
        
        if len(advanced_analyses) < min_advanced:
            return []
        
        if len(advanced_analyses) >= total_limit:
            return list(advanced_analyses[:total_limit])

        simple_limit = total_limit - len(advanced_analyses)
        
        advanced_video_ids = [video.id for video, _ in advanced_analyses]
        
        simple_stmt = select(Video, AIResponse).join(
            AIResponse, Video.id == AIResponse.video_id
        ).where(
            Video.user_id == user.id,
            Video.channel_id == channel_id,
            AIResponse.txt_file_path.isnot(None),
            AIResponse.chunk_id == 0,
            AIResponse.analysis_type == 'simple',
            ~Video.id.in_(advanced_video_ids),  
            Video.processed_at.isnot(None)
        ).order_by(Video.processed_at.asc()).limit(simple_limit)
        
        simple_result = await session.execute(simple_stmt)
        simple_analyses = simple_result.all()
        

        all_analyses = list(advanced_analyses) + list(simple_analyses)

        all_analyses.sort(key=lambda x: x[0].processed_at)

        return all_analyses


async def get_channel_analysis_stats(user_id: int, channel_id: str) -> dict:

    async with async_session() as session:
        user = await _resolve_user(session, user_id)
        
        if not user:
            return {'total': 0, 'advanced': 0, 'simple': 0}
        
        advanced_stmt = select(func.count(Video.id)).join(
            AIResponse, Video.id == AIResponse.video_id
        ).where(
            Video.user_id == user.id,
            Video.channel_id == channel_id,
            AIResponse.analysis_type.in_(['advanced', 'advanced_final']),
            AIResponse.chunk_id == 0,
            AIResponse.txt_file_path.isnot(None)
        )
        advanced_result = await session.execute(advanced_stmt)
        advanced = advanced_result.scalar() or 0

        simple_stmt = select(func.count(Video.id)).join(
            AIResponse, Video.id == AIResponse.video_id
        ).where(
            Video.user_id == user.id,
            Video.channel_id == channel_id,
            AIResponse.analysis_type == 'simple',
            AIResponse.chunk_id == 0,
            AIResponse.txt_file_path.isnot(None)
        )
        simple_result = await session.execute(simple_stmt)
        simple = simple_result.scalar() or 0
        
        total = advanced + simple
        
        return {
            'total': total,
            'advanced': advanced,
            'simple': simple
        }


async def get_channel_analysis_history(user_id: int, channel_id: str, limit: int = 10):

    balanced_analyses = await get_balanced_evolution_analyses(
        user_id=user_id,
        channel_id=channel_id,
        min_advanced=5,
        total_limit=limit
    )

    history = []
    for video, ai_response in balanced_analyses:
        history.append({
            'video_id': video.id,
            'video_url': video.video_url,
            'processed_at': video.processed_at,
            'txt_path': ai_response.txt_file_path,
            'analysis_type': ai_response.analysis_type
        })
    
    return history


async def ensure_user_exists(user_id: int) -> User:

    async with async_session() as session:
        # Foydalanuvchini qidirish
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            print(f"🔧 Foydalanuvchi {user_id} yaratilmoqda...")
            
            new_user = User(
                user_id=user_id,
                username=f"user_{user_id}",
                tariff_plan="free",
                analyses_limit=5,
                analyses_used=0
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            print(f"✅ Foydalanuvchi {user_id} yaratildi")
            return new_user
        
        return user
    

async def create_advanced_analysis_response(
    user_id: int, 
    video_id: int, 
    human_report: str,
    machine_data: str
):
    """Создает запись расширенного анализа с двумя типами данных"""
    async with async_session() as session:
        stmt = insert(AIResponse).values(
            user_id=user_id,
            video_id=video_id,
            chunk_id=0,
            analysis_type="advanced",
            response_text=human_report,
            machine_data=machine_data,  # 🆕 Сохраняем машиночитаемый отчет
            created_at=datetime.now(tz=timezone.utc)
        )
        await session.execute(stmt)
        await session.commit()

async def get_user_analysis_history(user_id: int) -> list[str]:
    """Returns last 10 completed analyses (final reports) for Strategic Hub.

    We take them from AIResponse (chunk_id=0) rather than VideoAnalysis,
    because the bot persists final reports there.

    `user_id` may be Telegram user_id or internal DB id.
    """
    async with async_session() as session:
        user = await _resolve_user(session, user_id)

        # TZ-2: prefer "best" advanced analyses selected by MultiAnalysisOptimizer
        best_q = await session.execute(
            select(AIResponse.response_text)
            .where(AIResponse.user_id == user.id)
            .where(AIResponse.chunk_id == 0)
            .where(AIResponse.analysis_type == "advanced")
            .where(AIResponse.is_for_strategic_hub == True)  # noqa: E712
            .order_by(AIResponse.created_at.desc())
            .limit(10)
        )
        best = [r[0] for r in best_q.all()]
        if len(best) >= 10:
            return best

        # Fallback: latest completed advanced final reports
        fallback_q = await session.execute(
            select(AIResponse.response_text)
            .where(AIResponse.user_id == user.id)
            .where(AIResponse.chunk_id == 0)
            .where(AIResponse.analysis_type.in_(["advanced", "advanced_final"]))
            .order_by(AIResponse.created_at.desc())
            .limit(10)
        )
        fallback = [r[0] for r in fallback_q.all()]

        # Merge preserving order (best first)
        out: list[str] = []
        seen = set()
        for item in best + fallback:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
            if len(out) >= 10:
                break
        return out


async def get_evolution_prompts(analysis_type: str = "evolution"):
    """
    Получение промптов для всех типов анализа стратегического хаба
    
    ВАЖНО: Для каждого типа нужно создать промпты в базе данных:
    - category = название функции (например, "audience_map")
    - analysis_type = "step1" или "step2"
    """
    prompt_config = {
        "audience_map": {
            "category": "audience_map",
            "step1": "step1",
            "step2": "step2"
        },
        "content_prediction": {
            "category": "content_prediction",
            "step1": "step1",
            "step2": "step2"
        },
        "channel_diagnostics": {
            "category": "channel_diagnostics",
            "step1": "step1",
            "step2": "step2"
        },
        "content_ideas": {
            "category": "content_ideas",
            "step1": "step1",
            "step2": "step2"
        },
        "viral_potential": {
            "category": "viral_potential",
            "step1": "step1",
            "step2": "step2"
        },
        "iterative_ideas": {
            "category": "iterative_ideas",
            "evaluator_creative": "evaluator_creative",
            "evaluator_analytical": "evaluator_analytical",
            "evaluator_practical": "evaluator_practical",
            "improver": "improver",
            "final_scenario": "final_scenario"
        },
        "evolution": {
            "category": "evolution",
            "step1": "step1",
            "step2": "step2"
        }
    }
    
    # Получаем конфигурацию для запрошенного типа
    config = prompt_config.get(analysis_type, prompt_config["evolution"])
    
    prompts = {}
    
    # Для каждого ключа в конфигурации получаем промпт из БД
    for key, analysis_type_value in config.items():
        if key == "category":
            continue
        
        # Получаем промпт: category = config["category"], analysis_type = analysis_type_value
        prompt_list = await get_prompts(
            category=config["category"],
            analysis_type=analysis_type_value
        )
        
        prompts[key] = prompt_list[0] if prompt_list else None
    
    return prompts


# Добавьте эту вспомогательную функцию для проверки наличия промптов
async def check_prompts_exist(analysis_type: str) -> dict:
    """
    Проверяет наличие всех необходимых промптов для типа анализа
    
    Returns:
        dict: {
            "exists": bool,
            "missing": list,
            "found": list
        }
    """
    prompts = await get_evolution_prompts(analysis_type)
    
    missing = []
    found = []
    
    for key, prompt in prompts.items():
        if prompt is None:
            missing.append(key)
        else:
            found.append(key)
    
    return {
        "exists": len(missing) == 0,
        "missing": missing,
        "found": found
    }

async def get_advanced_with_synthesis(category: str, db: AsyncSession):
    advanced = (
        await db.execute(
            select(Prompt)
            .where(
                Prompt.category == category,
                Prompt.analysis_type == "advanced"
            )
            .order_by(Prompt.order)
        )
    ).scalars().all()

    synthesis = (
        await db.execute(
            select(Prompt)
            .where(
                Prompt.category == category,
                Prompt.analysis_type == "synthesis"
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if not synthesis:
        raise ValueError("Synthesis prompt topilmadi")

    return {
        "advanced": advanced,
        "synthesis": synthesis
    }
# =========================
# Web Admin CRUD helpers
# =========================

async def admin_list_users(search: str = "", page: int = 1, limit: int = 20) -> list[User]:
    """List users for Web Admin.

    NOTE: `user_id` here is Telegram user_id (User.user_id).
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    if limit > 200:
        limit = 200

    async with async_session() as session:
        q = select(User)
        if search:
            like = f"%{search.lower()}%"
            q = q.where(
                (User.username.ilike(like))
                | (cast(User.user_id, String).ilike(like))
            )
        q = q.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        res = await session.execute(q)
        return list(res.scalars().all())


async def admin_get_user(user_id: int) -> User | None:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.user_id == user_id))
        return res.scalar_one_or_none()


async def admin_set_user_tariff(user_id: int, tariff: str) -> bool:
    async with async_session() as session:
        stmt = update(User).where(User.user_id == user_id).values(tariff_plan=tariff)
        res = await session.execute(stmt)
        await session.commit()
        return (res.rowcount or 0) > 0


async def admin_set_user_limit(user_id: int, new_limit: int) -> None:
    await set_user_limit(user_id, new_limit)


async def admin_reset_user_usage(user_id: int) -> None:
    await reset_user_analyses(user_id)


async def admin_list_prompts(category: str | None = None, analysis_type: str | None = None) -> list[Prompt]:
    """List prompts for Web Admin (same table as bot)."""
    async with async_session() as session:
        q = select(Prompt)
        if category:
            q = q.where(Prompt.category == category)
        if analysis_type:
            q = q.where(Prompt.analysis_type == analysis_type)
        q = q.order_by(func.coalesce(Prompt.order, 0), Prompt.id)
        res = await session.execute(q)
        return list(res.scalars().all())


async def admin_get_prompt(prompt_id: int) -> Prompt | None:
    async with async_session() as session:
        res = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
        return res.scalar_one_or_none()


async def admin_create_prompt(
    *,
    name: str,
    prompt_text: str,
    category: str = "my",
    analysis_type: str = "simple",
    module_id: str | None = None,
) -> Prompt:
    """Create prompt with stable ordering (next order within category+analysis_type)."""
    async with async_session() as session:
        max_order_res = await session.execute(
            select(func.max(func.coalesce(Prompt.order, 0)))
            .where(Prompt.category == category)
            .where(Prompt.analysis_type == analysis_type)
        )
        max_order = max_order_res.scalar_one_or_none()
        next_order = int(max_order or 0) + 1 if max_order is not None else 0

        p = Prompt(
            name=name,
            prompt_text=prompt_text,
            category=category,
            analysis_type=analysis_type,
            module_id=module_id,
            order=next_order,
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


async def admin_update_prompt(
    *,
    prompt_id: int,
    name: str,
    prompt_text: str,
    category: str = "my",
    analysis_type: str = "simple",
    module_id: str | None = None,
) -> Prompt | None:
    async with async_session() as session:
        res = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
        p = res.scalar_one_or_none()
        if not p:
            return None
        p.name = name
        p.prompt_text = prompt_text
        p.category = category
        p.analysis_type = analysis_type
        p.module_id = module_id
        if p.order is None:
            p.order = 0
        await session.commit()
        await session.refresh(p)
        return p


async def admin_delete_prompt(prompt_id: int) -> bool:
    async with async_session() as session:
        res = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
        p = res.scalar_one_or_none()
        if not p:
            return False
        await session.delete(p)
        await session.commit()
        return True


async def admin_reorder_prompts(orders: list[dict]) -> None:
    """Reorder prompts.

    `orders`: [{"id": 1, "order": 0}, ...]
    """
    async with async_session() as session:
        ids = [int(x["id"]) for x in orders]
        res = await session.execute(select(Prompt).where(Prompt.id.in_(ids)))
        items = {p.id: p for p in res.scalars().all()}
        missing = [pid for pid in ids if pid not in items]
        if missing:
            raise ValueError({"missing_prompt_ids": missing})

        for item in orders:
            pid = int(item["id"])
            ordv = int(item["order"])
            items[pid].order = ordv

        await session.commit()


# ---------- TZ-2: Multi-analysis evaluator prompts (ADVANCED ONLY) ----------

async def admin_list_multi_analysis_prompts() -> list[MultiAnalysisPrompt]:
    async with async_session() as session:
        res = await session.execute(select(MultiAnalysisPrompt).order_by(MultiAnalysisPrompt.updated_at.desc()))
        return list(res.scalars().all())


async def admin_create_multi_analysis_prompt(
    *,
    name: str,
    prompt_text: str,
    version: str | None = None,
    description: str | None = None,
    make_active: bool = False,
) -> MultiAnalysisPrompt:
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        if make_active:
            await session.execute(update(MultiAnalysisPrompt).values(is_active=False))

        p = MultiAnalysisPrompt(
            name=name,
            prompt_text=prompt_text,
            version=version or "1.0",
            description=description,
            is_active=bool(make_active),
            created_at=now,
            updated_at=now,
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


async def admin_update_multi_analysis_prompt(
    *,
    prompt_id: int,
    name: str | None = None,
    prompt_text: str | None = None,
    version: str | None = None,
    description: str | None = None,
) -> MultiAnalysisPrompt | None:
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        res = await session.execute(select(MultiAnalysisPrompt).where(MultiAnalysisPrompt.id == prompt_id))
        p = res.scalar_one_or_none()
        if not p:
            return None
        if name is not None:
            p.name = name
        if prompt_text is not None:
            p.prompt_text = prompt_text
        if version is not None:
            p.version = version
        if description is not None:
            p.description = description
        p.updated_at = now
        await session.commit()
        await session.refresh(p)
        return p


async def admin_activate_multi_analysis_prompt(prompt_id: int) -> bool:
    now = datetime.now(tz=timezone.utc)
    async with async_session() as session:
        res = await session.execute(select(MultiAnalysisPrompt).where(MultiAnalysisPrompt.id == prompt_id))
        p = res.scalar_one_or_none()
        if not p:
            return False

        await session.execute(update(MultiAnalysisPrompt).values(is_active=False))
        p.is_active = True
        p.updated_at = now
        await session.commit()
        return True


async def admin_delete_multi_analysis_prompt(prompt_id: int) -> bool:
    async with async_session() as session:
        res = await session.execute(select(MultiAnalysisPrompt).where(MultiAnalysisPrompt.id == prompt_id))
        p = res.scalar_one_or_none()
        if not p:
            return False
        was_active = bool(p.is_active)
        await session.delete(p)
        await session.commit()

    # Ensure there is always an active prompt if any exist.
    if was_active:
        async with async_session() as session:
            res = await session.execute(select(MultiAnalysisPrompt).order_by(MultiAnalysisPrompt.updated_at.desc()).limit(1))
            newest = res.scalar_one_or_none()
            if newest:
                await session.execute(update(MultiAnalysisPrompt).values(is_active=False))
                newest.is_active = True
                newest.updated_at = datetime.now(tz=timezone.utc)
                await session.commit()

    return True

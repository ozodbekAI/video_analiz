from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .engine import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    language = Column(String(10), default="ru")  # YANGI: til
    tariff_plan = Column(Boolean, default=False)
    analyses_limit = Column(Integer, default=5)  # Oylik limit
    analyses_used = Column(Integer, default=0)  # Ishlatilgan so'rovlar
    last_reset_date = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))  # YANGI
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    videos = relationship("Video", back_populates="user")


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_url = Column(Text, nullable=False)
    video_title = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    user = relationship("User", back_populates="videos")
    comments = relationship("Comment", back_populates="video")
    ai_responses = relationship("AIResponse", back_populates="video")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=True)
    chunk_id = Column(Integer, default=0)
    
    video = relationship("Video", back_populates="comments")


class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    analysis_type = Column(String(50), nullable=True)
    category = Column(String(50), default="my")


class AIResponse(Base):
    __tablename__ = "ai_responses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    chunk_id = Column(Integer, default=0)
    analysis_type = Column(String(50), nullable=True)
    response_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    video = relationship("Video", back_populates="ai_responses")
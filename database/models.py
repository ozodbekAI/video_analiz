from sqlalchemy import JSON, BigInteger, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .engine import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    language = Column(String(10), default="ru")
    
    tariff_plan = Column(String, default='starter')
    analyses_limit = Column(Integer, default=1) 
    analyses_used = Column(Integer, default=0)  
    last_reset_date = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    youtube_channel_id = Column(String(100), nullable=True)
    verification_method = Column(
        Enum('oauth', 'code', name='verification_method_enum'),
        nullable=True
    )
    verification_status = Column(
        Enum('pending', 'verified', 'failed', 'unverified', name='verification_status_enum'),
        default='unverified'
    )
    verification_date = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    videos = relationship("Video", back_populates="user")
    verification_attempts = relationship("VerificationAttempt", back_populates="user")


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    channel_url = Column(String(500), nullable=False)
    verification_code = Column(String(100), nullable=False)
    verification_method = Column(
        Enum('oauth', 'code', name='attempt_method_enum'),
        nullable=False
    )
    status = Column(
        Enum('pending', 'verified', 'failed', 'cancelled', name='attempt_status_enum'),
        default='pending'
    )
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="verification_attempts")


class SampleReport(Base):
    __tablename__ = "sample_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_name = Column(String(255), nullable=False)
    video_url = Column(String(500), nullable=False)
    video_type = Column(String(20), default='regular') 
    analysis_data = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_url = Column(Text, nullable=False)
    video_title = Column(Text, nullable=True)
    channel_id = Column(String(100), nullable=True) 
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
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    chunk_id = Column(Integer, default=0)
    analysis_type = Column(String(50), nullable=True)
    response_text = Column(Text, nullable=False)
    machine_data = Column(JSON, nullable=True)  
    txt_file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    
    video = relationship("Video", back_populates="ai_responses")



class EvolutionAnalysis(Base):

    __tablename__ = "evolution_analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    channel_id = Column(String(100), nullable=False)  
    channel_title = Column(String(255), nullable=True)  

    step1_response = Column(Text, nullable=True)  
    step2_response = Column(Text, nullable=True)  

    videos_analyzed = Column(Integer, default=0)  
    analysis_period = Column(String(100), nullable=True)  
    video_ids_used = Column(JSON, nullable=True)  

    pdf_path = Column(String(500), nullable=True)
    txt_path = Column(String(500), nullable=True)

    status = Column(
        Enum('pending', 'processing', 'completed', 'failed', name='evolution_status_enum'),
        default='pending'
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="evolution_analyses")
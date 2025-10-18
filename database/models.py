from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String)
    language = Column(String, default='ru')
    tariff_plan = Column(String, default='basic')
    analyses_used = Column(Integer, default=0)
    analyses_limit = Column(Integer, default=999)
    subscription_reset_date = Column(Date)
    created_at = Column(DateTime(timezone=True)) 

class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    video_url = Column(String)
    video_title = Column(String)
    processed_at = Column(DateTime(timezone=True)) 

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    video_id = Column(Integer, ForeignKey('videos.id'))
    raw_text = Column(Text)
    cleaned_text = Column(Text)
    is_cleaned = Column(Boolean, default=False)
    chunk_id = Column(Integer)
    timestamp = Column(DateTime(timezone=True)) 

class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    prompt_text = Column(Text)
    analysis_type = Column(String)  
    category = Column(String)  

class AIResponse(Base):
    __tablename__ = 'ai_responses'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    video_id = Column(Integer, ForeignKey('videos.id'))
    chunk_id = Column(Integer)
    analysis_type = Column(String)
    response_text = Column(Text)
    created_at = Column(DateTime(timezone=True)) 
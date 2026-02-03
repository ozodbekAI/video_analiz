#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модели данных для YouTube парсера"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class VideoInfo:
    """Информация о видео"""
    id: str
    video_type: str = "video"  # "video" или "shorts"
    title: str = ""
    channel_title: str = ""
    channel_id: str = ""
    published_at: str = ""
    description: str = ""
    duration: str = ""
    duration_seconds: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        # Для краткости в TXT не включаем теги
        data.pop('tags', None)
        return data
    
    @property
    def is_shorts(self) -> bool:
        return self.video_type == "shorts"
    
    @property
    def is_short_form(self) -> bool:
        """Определение короткого контента по длительности"""
        return self.duration_seconds <= 60 or self.video_type == "shorts"


@dataclass
class Comment:
    """Комментарий"""
    id: str
    video_id: str
    author: str = ""
    author_id: str = ""
    text: str = ""
    text_clean: str = ""
    published_at: str = ""
    like_count: int = 0
    reply_count: int = 0
    parent_id: Optional[str] = None
    replies: List['Comment'] = None
    
    def __post_init__(self):
        if self.replies is None:
            self.replies = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['replies'] = [reply.to_dict() for reply in self.replies]
        return data
    
    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None


@dataclass
class ParsingResult:
    """Результат парсинга видео"""
    video: VideoInfo
    comments: List[Comment]
    statistics: Dict
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            'video': self.video.to_dict(),
            'comments': [c.to_dict() for c in self.comments],
            'statistics': self.statistics,
            'metadata': {
                'total_comments': len(self.comments),
                'parsed_at': datetime.now().isoformat(),
                'video_type': self.video.video_type,
                'is_shorts': self.video.is_shorts
            }
        }

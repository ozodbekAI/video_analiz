#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Утилиты для YouTube парсера"""

import re
import sys
import time
import html
import logging
from functools import wraps
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime


def log_errors(func):
    """Декоратор для обработки ошибок"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Ошибка в {func.__name__}: {str(e)}")
            return None
    return wrapper


def extract_video_id(url: str) -> Tuple[Optional[str], str]:
    """
    Извлечение ID видео из URL с поддержкой Shorts
    
    Args:
        url: URL видео
    
    Returns:
        Кортеж (video_id, video_type)
    """
    if not url or not isinstance(url, str):
        return None, "video"
    
    url = url.strip()
    
    # Паттерны для различных форматов URL
    patterns = [
        (r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^&\n?#]+)', 'shorts'),
        (r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\n?#]+)', 'video'),
        (r'(?:https?://)?(?:www\.)?youtu\.be/([^&\n?#]+)', 'video'),
        (r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&\n?#]+)', 'video'),
        (r'(?:https?://)?(?:www\.)?youtube\.com/v/([^&\n?#]+)', 'video'),
        (r'(?:https?://)?(?:www\.)?m\.youtube\.com/watch\?v=([^&\n?#]+)', 'video'),
        (r'(?:https?://)?(?:www\.)?youtube\.com/live/([^&\n?#]+)', 'live'),
    ]
    
    for pattern, video_type in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1), video_type
    
    return None, "video"


def clean_text(text: str) -> str:
    """Очистка текста от HTML и форматирования"""
    if not text:
        return ""
    
    # Декодирование HTML-сущностей
    text = html.unescape(text)
    
    # Удаление HTML-тегов
    text = re.sub(r'<[^>]+>', '', text)
    
    # Замена спецсимволов
    replacements = {
        '&quot;': '"',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' ',
        '&#39;': "'",
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Удаление лишних пробелов
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def format_number(num: int) -> str:
    """Форматирование чисел с разделителями"""
    try:
        return f"{num:,}".replace(',', ' ')
    except (ValueError, TypeError):
        return str(num)


def format_duration(seconds: int) -> str:
    """Форматирование длительности в формат HH:MM:SS"""
    try:
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"


def create_results_dir() -> Path:
    """Создание директории для результатов"""
    try:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        return results_dir
    except:
        return Path(".")


def get_unique_filename(video_id: str, video_type: str = "video", extension: str = "txt") -> Path:
    """Получение уникального имени файла"""
    results_dir = create_results_dir()
    timestamp = time.strftime("%d.%m.%Y-%H.%M.%S")
    prefix = "shorts" if video_type == "shorts" else "video"
    base = f"{prefix}_{video_id}_{timestamp}"
    filename = f"{base}.{extension}"
    return results_dir / filename


def validate_video_id(video_id: str) -> bool:
    """Валидация ID видео"""
    if not video_id or not isinstance(video_id, str):
        return False
    
    video_id = video_id.strip()
    
    # Стандартные видео ID: 11 символов
    if len(video_id) == 11:
        return all(c.isalnum() or c in '-_' for c in video_id)
    
    # Shorts могут иметь разную длину
    if 4 <= len(video_id) <= 20:
        return all(c.isalnum() or c in '-_' for c in video_id)
    
    return False


class StatisticsCalculator:
    """Калькулятор статистики"""
    
    @staticmethod
    def calculate_video_stats(video_info: any, comments: List[any], video_type: str = "video") -> Dict:
        """Расчет статистики видео"""
        total_comments = len(comments)
        total_top_level = sum(1 for c in comments if not c.is_reply)
        total_replies = total_comments - total_top_level
        total_likes = sum(c.like_count for c in comments)
        avg_likes_per_comment = total_likes / total_comments if total_comments > 0 else 0
        
        most_liked = max(comments, key=lambda c: c.like_count) if comments else None
        
        # Подсчет активных авторов
        authors = {}
        for comment in comments:
            if comment.author not in authors:
                authors[comment.author] = {'comments': 0, 'likes': 0, 'replies': 0}
            authors[comment.author]['comments'] += 1
            authors[comment.author]['likes'] += comment.like_count
            if comment.is_reply:
                authors[comment.author]['replies'] += 1
        
        most_active = max(authors.items(), key=lambda x: x[1]['comments']) if authors else None
        
        return {
            'video_info': {
                'engagement_rate': (total_likes / video_info.view_count * 100) if video_info.view_count > 0 else 0,
            },
            'summary': {
                'total_interactions': total_likes,
                'comment_to_view_ratio': total_comments / video_info.view_count if video_info.view_count > 0 else 0,
                'like_to_view_ratio': total_likes / video_info.view_count if video_info.view_count > 0 else 0,
            },
            'comment_statistics': {
                'total_comments': total_comments,
                'total_top_level': total_top_level,
                'total_replies': total_replies,
                'unique_authors': len(authors),
                'total_likes': total_likes,
                'avg_likes_per_comment': avg_likes_per_comment,
                'most_liked_comment': {
                    'author': most_liked.author,
                    'text': most_liked.text[:100] + '...' if len(most_liked.text) > 100 else most_liked.text,
                    'likes': most_liked.like_count,
                } if most_liked else None,
                'most_active_author': {
                    'author': most_active[0],
                    'comments': most_active[1]['comments'],
                    'likes': most_active[1]['likes'],
                    'replies': most_active[1]['replies'],
                } if most_active else None,
            }
        }


def setup_logging():
    """Настройка логирования"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    except Exception:
        return None


# Инициализация логгера
logger = setup_logging()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube Data API v3 клиент с поддержкой Shorts"""

import time
from typing import List, Dict, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils import log_errors, format_duration, clean_text
from data_models import VideoInfo, Comment
import settings


class YouTubeAPI:
    """Клиент для работы с YouTube API (поддерживает Shorts)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.API_KEY
        self.youtube = build("youtube", "v3", developerKey=self.api_key)
        self._request_count = 0
    
    def _make_request(self, request):
        """Выполнение запроса с задержкой"""
        self._request_count += 1
        time.sleep(settings.REQUEST_DELAY)
        return request.execute()
    
    @log_errors
    def get_video_info(self, video_id: str, video_type: str = "video") -> Optional[VideoInfo]:
        """
        Получение информации о видео или Shorts
        """
        try:
            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id,
                fields="items(id,snippet(title,description,channelId,channelTitle,publishedAt,tags),statistics,contentDetails(duration))"
            )
            
            response = self._make_request(request)
            
            if not response.get('items'):
                print(f"⚠️  Видео {video_id} не найдено или недоступно")
                return None
            
            item = response['items'][0]
            snippet = item.get('snippet', {})
            stats = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            # Преобразование длительности ISO 8601 в секунды
            duration_iso = content_details.get('duration', 'PT0S')
            duration_seconds = self._parse_duration(duration_iso)
            
            # Определяем тип видео
            final_video_type = video_type
            if duration_seconds <= 60 and video_type == "video":
                # Если видео короче 60 секунд, это может быть Shorts
                final_video_type = "shorts"
            
            return VideoInfo(
                id=video_id,
                video_type=final_video_type,
                title=snippet.get('title', ''),
                channel_title=snippet.get('channelTitle', ''),
                channel_id=snippet.get('channelId', ''),
                published_at=snippet.get('publishedAt', '').replace('T', ' ').replace('Z', ''),
                description=snippet.get('description', ''),
                duration=format_duration(duration_seconds),
                duration_seconds=duration_seconds,
                view_count=int(stats.get('viewCount', 0)),
                like_count=int(stats.get('likeCount', 0)),
                comment_count=int(stats.get('commentCount', 0)),
                tags=snippet.get('tags', [])
            )
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ Видео {video_id} не найдено (ошибка 404)")
            elif e.resp.status == 403:
                print(f"❌ Доступ к видео {video_id} запрещен (ошибка 403)")
            else:
                print(f"❌ HTTP ошибка при получении информации о видео: {e}")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None
    
    @log_errors
    def get_video_comments(self, video_id: str, video_type: str = "video", max_comments: int = 0) -> List[Comment]:
        """
        Получение комментариев видео с пагинацией
        max_comments: 0 = все комментарии, N = максимум N комментариев
        """
        all_comments = []
        next_page_token = None
        page_count = 0
        
        # Определяем лимит
        if max_comments <= 0:
            max_comments = float('inf')  # Бесконечность
        
        print(f"   🔍 Поиск комментариев (лимит: {'все' if max_comments == float('inf') else max_comments})...")
        
        try:
            while len(all_comments) < max_comments:
                page_count += 1
                
                # Определяем сколько комментариев запросить на этой странице
                max_per_page = 100  # Максимум для YouTube API
                remaining = max_comments - len(all_comments)
                to_fetch = min(max_per_page, remaining) if max_comments != float('inf') else max_per_page
                
                request = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=to_fetch,
                    pageToken=next_page_token,
                    order=settings.SORT_ORDER,
                    textFormat="plainText"
                )
                
                response = self._make_request(request)
                
                # Если нет комментариев
                if not response.get('items'):
                    if page_count == 1:  # Если это первый запрос и нет комментариев
                        print(f"   ℹ️  У видео нет комментариев или они отключены")
                    break
                
                batch_comments = []
                for item in response.get('items', []):
                    # Основной комментарий
                    top_comment = item['snippet']['topLevelComment']
                    top_comment_snippet = top_comment['snippet']
                    
                    main_comment = Comment(
                        id=top_comment['id'],
                        video_id=video_id,
                        author=top_comment_snippet.get('authorDisplayName', ''),
                        author_id=top_comment_snippet.get('authorChannelId', {}).get('value', ''),
                        text=top_comment_snippet.get('textDisplay', ''),
                        text_clean=clean_text(top_comment_snippet.get('textDisplay', '')),
                        published_at=top_comment_snippet.get('publishedAt', '').replace('T', ' ').replace('Z', ''),
                        like_count=int(top_comment_snippet.get('likeCount', 0)),
                        reply_count=int(item['snippet'].get('totalReplyCount', 0))
                    )
                    
                    # Ответы
                    if settings.COLLECT_REPLIES and 'replies' in item:
                        for reply in item['replies']['comments']:
                            reply_snippet = reply['snippet']
                            reply_comment = Comment(
                                id=reply['id'],
                                video_id=video_id,
                                author=reply_snippet.get('authorDisplayName', ''),
                                author_id=reply_snippet.get('authorChannelId', {}).get('value', ''),
                                text=reply_snippet.get('textDisplay', ''),
                                text_clean=clean_text(reply_snippet.get('textDisplay', '')),
                                published_at=reply_snippet.get('publishedAt', '').replace('T', ' ').replace('Z', ''),
                                like_count=int(reply_snippet.get('likeCount', 0)),
                                parent_id=main_comment.id
                            )
                            main_comment.replies.append(reply_comment)
                    
                    batch_comments.append(main_comment)
                
                all_comments.extend(batch_comments)
                print(f"   📥 Страница {page_count}: {len(batch_comments)} комментариев (всего: {len(all_comments)})")
                
                # Проверяем, есть ли следующая страница
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    print(f"   ✅ Все комментарии получены")
                    break
                
                # Если достигли лимита
                if len(all_comments) >= max_comments:
                    print(f"   ⏹️  Достигнут лимит в {max_comments} комментариев")
                    break
                    
        except HttpError as e:
            if e.resp.status == 403:
                print(f"   ⚠️  Комментарии недоступны для этого видео (возможно, ограничения)")
            else:
                print(f"   ⚠️  Ошибка при получении комментариев: {e}")
        except Exception as e:
            print(f"   ⚠️  Непредвиденная ошибка: {e}")
        
        return all_comments
    
    def _parse_duration(self, duration_str: str) -> int:
        """Парсинг длительности в формате ISO 8601"""
        import re
        
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        
        return hours * 3600 + minutes * 60 + seconds
    
    @property
    def request_count(self) -> int:
        """Количество выполненных запросов"""
        return self._request_count

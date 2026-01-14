import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config

config = Config()
youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def extract_video_id(url):
    """Video ID ni URL dan ajratib olish"""
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&?\n]+)",
        r"(?:www\.)?youtube\.com\/watch\?.*v=([^&?\n]+)",
        r"(?:www\.)?youtu\.be\/([^&?\n]+)",
        r"(?:www\.)?youtube\.com\/embed\/([^&?\n]+)",
        r"(?:www\.)?youtube\.com\/shorts\/([^&?\n]+)"
    ]
    
    url_without_https = url.replace("https://", "").replace("http://", "")
    
    for pattern in patterns:
        match = re.search(pattern, url_without_https)
        if match:
            video_id = match.group(1)
            spec = ("?", "&", "/")
            if any(char in video_id for char in spec):
                video_id = video_id.split("?")[0]
                video_id = video_id.split("&")[0]
                video_id = video_id.split("/")[0]
            return video_id
    
    raise ValueError("Invalid YouTube URL")


def get_video_metadata(video_id: str) -> Optional[Dict]:
    """Video metadata ni olish"""
    try:
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
        
        item = response['items'][0]
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})
        
        # Duration ni aniqlash
        duration_str = content_details.get('duration', 'PT0S')
        import isodate
        duration_seconds = int(isodate.parse_duration(duration_str).total_seconds())
        is_shorts = duration_seconds <= 60
        
        return {
            'id': video_id,
            'title': snippet.get('title', ''),
            'published_at': snippet.get('publishedAt', ''),
            'channel_id': snippet.get('channelId', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'views': int(statistics.get('viewCount', 0)),
            'likes': int(statistics.get('likeCount', 0)),
            'comments': int(statistics.get('commentCount', 0)),
            'duration_seconds': duration_seconds,
            'is_shorts': is_shorts
        }
    except Exception as e:
        print(f"❌ Metadata olishda xato: {e}")
        return None


def get_video_comments_with_metrics(video_id: str, video_metadata: Dict = None) -> Dict:
    """
    Kommentarlarni + barcha metrikalarni olish (har doim metrics qaytaradi)
    """
    comments_data = []
    next_page_token = None

    # Metadata yo‘q bo‘lsa, har holda dict qaytaramiz
    if not video_metadata:
        video_metadata = get_video_metadata(video_id) or {}

    # Video publish vaqti
    try:
        published_at = video_metadata.get("published_at")
        if published_at:
            video_publish_time = datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        else:
            video_publish_time = datetime.now()
    except Exception:
        video_publish_time = datetime.now()

    # Kommentarlarni to'plash
    while True:
        try:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                order="relevance",
                textFormat="plainText",
            )

            response = request.execute()

            for item in response.get("items", []):
                top_comment = item["snippet"]["topLevelComment"]["snippet"]

                # Vaqt hisoblash (video chiqish vaqtidan keyin necha soat)
                try:
                    comment_time = datetime.fromisoformat(
                        top_comment["publishedAt"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    hours_after = (comment_time - video_publish_time).total_seconds() / 3600
                except Exception:
                    hours_after = 0

                main_comment = {
                    "time": top_comment["publishedAt"].replace("T", " ").replace("Z", ""),
                    "hours_after_video": round(hours_after, 2),
                    "author": top_comment.get("authorDisplayName", "Unknown"),
                    "likes": top_comment.get("likeCount", 0),
                    "text": top_comment.get("textDisplay", "").replace("\n", " "),
                    "replies": [],
                }

                # Javoblarni qo'shish
                if "replies" in item and item["replies"].get("comments"):
                    for reply in item["replies"]["comments"]:
                        reply_snippet = reply["snippet"]

                        try:
                            reply_time = datetime.fromisoformat(
                                reply_snippet["publishedAt"].replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                            reply_hours = (reply_time - video_publish_time).total_seconds() / 3600
                        except Exception:
                            reply_hours = 0

                        main_comment["replies"].append(
                            {
                                "time": reply_snippet["publishedAt"].replace("T", " ").replace("Z", ""),
                                "hours_after_video": round(reply_hours, 2),
                                "author": reply_snippet.get("authorDisplayName", "Unknown"),
                                "likes": reply_snippet.get("likeCount", 0),
                                "text": reply_snippet.get("textDisplay", "")
                                .replace("\n", " ")
                                .replace("@@", "@"),
                            }
                        )

                comments_data.append(main_comment)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(0.1)

        except HttpError as e:
            if "commentsDisabled" in str(e):
                print(f"⚠️ Kommentarlar o'chirilgan: {video_id}")
            else:
                print(f"❌ YouTube API xatosi: {e}")
            break
        except Exception as e:
            print(f"❌ Kommentarlarni olishda xato: {e}")
            break

    # METRIKALARNI HAR DOIM HISOBLAYMIZ
    metrics = calculate_engagement_metrics(comments_data, video_metadata)
    engagement_phases = calculate_engagement_phases(comments_data)
    top_authors = calculate_top_authors(comments_data, top_n=10)

    return {
        "comments": comments_data,
        "metadata": video_metadata,
        "metrics": metrics,
        "engagement_phases": engagement_phases,
        "top_authors": top_authors,
    }

    
    # METRIKALARNI HISOBLASH
    metrics = calculate_engagement_metrics(comments_data, video_metadata)
    engagement_phases = calculate_engagement_phases(comments_data)
    top_authors = calculate_top_authors(comments_data, top_n=10)
    
    return {
        'comments': comments_data,
        'metadata': video_metadata,
        'metrics': metrics,
        'engagement_phases': engagement_phases,
        'top_authors': top_authors
    }


def calculate_engagement_metrics(comments_data: List[Dict], video_metadata: Dict) -> Dict:
    """Engagement metrikalarni hisoblash"""
    total_comments = len(comments_data)
    total_replies = sum(len(c.get('replies', [])) for c in comments_data)
    total_engagement = total_comments + total_replies
    
    # Engagement rate
    views = video_metadata.get('views', 1)
    likes = video_metadata.get('likes', 0)
    engagement_rate = ((likes + total_engagement) / max(1, views)) * 100
    
    # Like ratio
    like_ratio = (likes / max(1, views)) * 100
    
    # Comment velocity (kommentlar/soat)
    if comments_data:
        max_hours = max(c.get('hours_after_video', 0) for c in comments_data)
        comment_velocity = total_comments / max(1, max_hours)
    else:
        comment_velocity = 0
    
    # Vaqt taqsimoti
    time_distribution = {
        '0-1h': 0,
        '1-6h': 0,
        '6-24h': 0,
        '24h+': 0
    }
    
    for comment in comments_data:
        hours = comment.get('hours_after_video', 0)
        if hours <= 1:
            time_distribution['0-1h'] += 1
        elif hours <= 6:
            time_distribution['1-6h'] += 1
        elif hours <= 24:
            time_distribution['6-24h'] += 1
        else:
            time_distribution['24h+'] += 1
    
    return {
        'total_comments': total_comments,
        'total_replies': total_replies,
        'total_engagement': total_engagement,
        'engagement_rate': round(engagement_rate, 2),
        'like_ratio': round(like_ratio, 2),
        'comment_velocity': round(comment_velocity, 2),
        'time_distribution': time_distribution
    }


def calculate_engagement_phases(comments_data: List[Dict]) -> Dict:
    """Vaqt fazalarini aniqlash"""
    phases = {
        'first_hour': (0, 1),
        'first_6h': (1, 6),
        'first_24h': (6, 24),
        'first_week': (24, 168),
        'long_tail': (168, float('inf'))
    }
    
    phase_stats = {}
    for phase_name, (start, end) in phases.items():
        phase_comments = [
            c for c in comments_data 
            if start <= c.get('hours_after_video', 0) < end
        ]
        phase_replies = sum(len(c.get('replies', [])) for c in phase_comments)
        
        phase_stats[phase_name] = {
            'comments': len(phase_comments),
            'replies': phase_replies,
            'total_engagement': len(phase_comments) + phase_replies
        }
    
    return phase_stats


def calculate_top_authors(comments_data: List[Dict], top_n: int = 10) -> List[Dict]:
    """Top authorlarni aniqlash"""
    authors = {}
    
    for comment in comments_data:
        author = comment.get('author', 'Unknown')
        if author not in authors:
            authors[author] = {
                'author': author,
                'comments': 0,
                'replies': 0,
                'total_likes': 0,
                'total_posts': 0
            }
        
        authors[author]['comments'] += 1
        authors[author]['total_likes'] += comment.get('likes', 0)
        authors[author]['total_posts'] += 1
        
        # Javoblarni sanash
        for reply in comment.get('replies', []):
            reply_author = reply.get('author', 'Unknown')
            if reply_author not in authors:
                authors[reply_author] = {
                    'author': reply_author,
                    'comments': 0,
                    'replies': 0,
                    'total_likes': 0,
                    'total_posts': 0
                }
            
            authors[reply_author]['replies'] += 1
            authors[reply_author]['total_likes'] += reply.get('likes', 0)
            authors[reply_author]['total_posts'] += 1
    
    # Sortlash va top N ni qaytarish
    sorted_authors = sorted(
        authors.values(),
        key=lambda x: x['total_posts'],
        reverse=True
    )
    
    return sorted_authors[:top_n]


# ESKI FUNKSIYALARNI SAQLASH (backward compatibility)
def get_video_comments(video_id):
    """
    ESKI: Oddiy kommentarlar ro'yxatini qaytaradi
    Backward compatibility uchun saqlanadi
    """
    result = get_video_comments_with_metrics(video_id)
    return result['comments']


# ===== BARCHA QOLGAN FUNKSIYALAR (ESKI) =====

def save_comments_to_file(comments_data, file_path):
    """Kommentarlarni faylga saqlash"""
    with open(file_path, "w", encoding="utf-8") as f:
        for comment in comments_data:
            # Yangi va eski formatni qo'llab-quvvatlash
            time_key = comment.get('time') or comment.get('time', '')
            author_key = comment.get('author') or comment.get('author', 'Unknown')
            likes_key = comment.get('likes', 0)
            text_key = comment.get('text') or comment.get('text', '')
            
            f.write(f"[{time_key}] ({author_key}, {likes_key} likes) {text_key}\n")
            
            if comment.get("replies"):
                f.write("{\n")
                for reply in comment["replies"]:
                    reply_time = reply.get('time', '')
                    reply_author = reply.get('author', 'Unknown')
                    reply_likes = reply.get('likes', 0)
                    reply_text = reply.get('text', '')
                    f.write(f"\t[{reply_time}] ({reply_author}, {reply_likes} likes) {reply_text}\n")
                f.write("}\n")
            f.write("\n\n")


def get_comments_file_path(video_id):
    """Kommentarlar fayl yo'lini olish"""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%d.%m.%Y-%H.%M.%S')
    file_path = results_dir / f"{video_id}_{timestamp}.txt"
    return str(file_path)


def get_video_comments_count(video_url: str) -> int:
    """Kommentarlar sonini olish"""
    try:
        video_id = extract_video_id(video_url)
        metadata = get_video_metadata(video_id)
        return metadata.get('comments', 0) if metadata else 0
    except Exception as e:
        print(f"❌ Kommentarlar sonini olishda xato: {e}")
        return 0


def parse_timestamps(description: str) -> List[Dict[str, str]]:
    """Timestamps ni description dan ajratib olish"""
    timestamps = []
    
    patterns = [
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]\s*(.+?)(?=\n|$)',
        r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?)(?=\n|$)',
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s+([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ].+?)(?=\n|$)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, description, re.MULTILINE)
        for match in matches:
            time_code = match.group(1).strip()
            title = match.group(2).strip()
            
            if title and len(title) > 2:
                timestamps.append({
                    "time": time_code,
                    "title": title
                })
    
    def time_to_seconds(time_str: str) -> int:
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    
    unique_timestamps = []
    seen_times = set()
    
    for ts in timestamps:
        if ts['time'] not in seen_times:
            seen_times.add(ts['time'])
            unique_timestamps.append(ts)
    
    unique_timestamps.sort(key=lambda x: time_to_seconds(x['time']))
    
    return unique_timestamps


async def get_video_description(video_url: str) -> str:
    """Video description ni olish"""
    try:
        video_id = extract_video_id(video_url)
        
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        request = youtube_client.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise ValueError("Video topilmadi")
        
        snippet = response['items'][0]['snippet']
        description = snippet.get('description', '')
        
        return description
        
    except Exception as e:
        raise Exception(f"Video description olishda xatolik: {str(e)}")


async def get_video_timestamps(video_url: str) -> Dict:
    """Video timestamps ni olish"""
    try:
        video_id = extract_video_id(video_url)
        
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        request = youtube_client.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise ValueError("Video topilmadi")
        
        snippet = response['items'][0]['snippet']
        title = snippet.get('title', '')
        description = snippet.get('description', '')
        
        timestamps = parse_timestamps(description)
        
        return {
            'video_id': video_id,
            'title': title,
            'description': description,
            'timestamps': timestamps,
            'has_timestamps': len(timestamps) > 0,
            'timestamps_count': len(timestamps)
        }
        
    except Exception as e:
        return {
            'video_id': extract_video_id(video_url) if video_url else None,
            'title': '',
            'description': '',
            'timestamps': [],
            'has_timestamps': False,
            'timestamps_count': 0
        }


def format_timestamps_for_analysis(timestamps: List[Dict[str, str]]) -> str:
    """Timestamps ni analiz uchun formatlash"""
    if not timestamps:
        return ""
    
    output = "\n\n=== VIDEO PERESKAZKA (TIMESTAMPS) ===\n\n"
    for idx, ts in enumerate(timestamps, 1):
        output += f"{idx}. {ts['time']} - {ts['title']}\n"
    
    return output


def extract_channel_id_from_url(channel_url: str) -> Optional[str]:
    """Kanal URL dan kanal ID ni ajratib olish"""
    patterns = [
        (r'youtube\.com/@([^/?]+)', 'handle'),
        (r'youtube\.com/channel/([^/?]+)', 'id'),
        (r'youtube\.com/c/([^/?]+)', 'custom'),
        (r'youtube\.com/user/([^/?]+)', 'username')
    ]
    
    for pattern, url_type in patterns:
        match = re.search(pattern, channel_url)
        if match:
            identifier = match.group(1)
            return identifier, url_type
    
    return None, None


async def get_channel_id_by_handle(handle: str) -> Optional[str]:
    """Handle orqali kanal ID ni topish"""
    try:
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        clean_handle = handle.lstrip('@')
        
        try:
            request = youtube_client.channels().list(
                part='snippet',
                forHandle=clean_handle
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['id']
        except Exception as e:
            print(f"forHandle ishlamadi: {e}")
        
        try:
            request = youtube_client.channels().list(
                part='snippet',
                forUsername=clean_handle
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['id']
        except Exception as e:
            print(f"forUsername ishlamadi: {e}")
        
        try:
            request = youtube_client.search().list(
                part='snippet',
                q=f"@{clean_handle}",
                type='channel',
                maxResults=5
            )
            response = request.execute()
            
            if response.get('items'):
                for item in response['items']:
                    channel_title = item['snippet']['channelTitle'].lower()
                    if clean_handle.lower() in channel_title or clean_handle.lower().replace('_', '') in channel_title.replace(' ', ''):
                        return item['snippet']['channelId']
                
                return response['items'][0]['snippet']['channelId']
        except Exception as e:
            print(f"Search API ishlamadi: {e}")
        
        return None
        
    except Exception as e:
        print(f"Handle orqali kanal topishda xatolik: {e}")
        return None


async def get_channel_description(channel_url: str) -> str:
    """Kanal description ni olish"""
    try:
        identifier, url_type = extract_channel_id_from_url(channel_url)
        
        if not identifier:
            raise ValueError("Kanal URL formati noto'g'ri")
        
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        channel_id = None
        
        if url_type == 'id' and identifier.startswith('UC') and len(identifier) == 24:
            channel_id = identifier
        elif url_type == 'handle':
            channel_id = await get_channel_id_by_handle(identifier)
        elif url_type in ['custom', 'username']:
            try:
                request = youtube_client.channels().list(
                    part='snippet',
                    forUsername=identifier
                )
                response = request.execute()
                
                if response.get('items'):
                    channel_id = response['items'][0]['id']
            except Exception:
                pass
            
            if not channel_id:
                try:
                    request = youtube_client.search().list(
                        part='snippet',
                        q=identifier,
                        type='channel',
                        maxResults=5
                    )
                    response = request.execute()
                    
                    if response.get('items'):
                        for item in response['items']:
                            channel_title = item['snippet']['channelTitle'].lower()
                            if identifier.lower() in channel_title or identifier.lower().replace('_', '') in channel_title.replace(' ', ''):
                                channel_id = item['snippet']['channelId']
                                break
                        
                        if not channel_id:
                            channel_id = response['items'][0]['snippet']['channelId']
                except Exception:
                    pass
        
        if not channel_id:
            raise ValueError(f"Kanal topilmadi: {identifier}")
        
        request = youtube_client.channels().list(
            part='snippet',
            id=channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise ValueError(f"Kanal ma'lumotlari topilmadi. Channel ID: {channel_id}")
        
        description = response['items'][0]['snippet'].get('description', '')
        
        return description
    
    except HttpError as e:
        if e.resp.status == 403:
            raise Exception("YouTube API quota tugadi yoki kalit yaroqsiz")
        elif e.resp.status == 404:
            raise Exception("Kanal topilmadi")
        else:
            raise Exception(f"YouTube API xatosi: {e}")
    
    except Exception as e:
        raise Exception(f"Kanal tavsifini olishda xatolik: {str(e)}")


async def get_video_channel_info(video_url: str) -> Optional[Dict[str, str]]:
    """Video kanalining ma'lumotlarini olish"""
    try:
        video_id = extract_video_id(video_url)
        
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        request = youtube_client.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
        
        snippet = response['items'][0]['snippet']
        channel_id = snippet['channelId']
        channel_title = snippet['channelTitle']
        
        return {
            'channel_id': channel_id,
            'channel_url': f"https://www.youtube.com/channel/{channel_id}",
            'channel_title': channel_title
        }
        
    except Exception as e:
        print(f"Video kanal ma'lumotlarini olishda xatolik: {e}")
        return None


async def get_channel_info_by_id(channel_id: str) -> dict:
    """Kanal ID orqali to'liq ma'lumotlarni olish"""
    try:
        youtube_client = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        clean_channel_id = channel_id
        
        if channel_id.startswith('@'):
            clean_channel_id = await get_channel_id_by_handle(channel_id)
            if not clean_channel_id:
                raise ValueError(f"Handle topilmadi: {channel_id}")
        
        request = youtube_client.channels().list(
            part='snippet,statistics',
            id=clean_channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise ValueError(f"Kanal topilmadi: {channel_id}")
        
        item = response['items'][0]
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        
        return {
            'id': item['id'],
            'title': snippet.get('title', 'Unknown Channel'),
            'description': snippet.get('description', ''),
            'subscriber_count': int(statistics.get('subscriberCount', 0)),
            'video_count': int(statistics.get('videoCount', 0))
        }
        
    except Exception as e:
        print(f"Kanal ma'lumotlarini olishda xatolik: {e}")
        return {
            'id': channel_id,
            'title': channel_id[:30] if len(channel_id) > 30 else channel_id,
            'description': '',
            'subscriber_count': 0,
            'video_count': 0
        }


def is_shorts_url(url: str) -> bool:
    """URL Shorts ekanligini tekshirish"""
    return "/shorts/" in url.lower()


async def is_shorts_video(url: str) -> bool:
    """Video Shorts ekanligini aniqlash"""
    try:
        if is_shorts_url(url):
            return True
        
        video_id = extract_video_id(url)
        metadata = get_video_metadata(video_id)
        
        return metadata.get('is_shorts', False) if metadata else False
        
    except Exception as e:
        print(f"Shorts aniqlashda xatolik: {e}")
        return is_shorts_url(url)


def get_video_comments_shorts_safe(video_id: str, max_results: int = 1000):
    """Shorts uchun xavfsiz kommentarlar olish"""
    import time
    
    comments_data = []
    next_page_token = None
    total_fetched = 0
    max_retries = 3
    retry_count = 0
    
    while total_fetched < max_results:
        try:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_results - total_fetched),
                pageToken=next_page_token,
                order="relevance",
                textFormat="plainText"
            )
            
            response = request.execute()
            
            for item in response["items"]:
                top_comment = item["snippet"]["topLevelComment"]["snippet"]
                
                time_comm = top_comment["publishedAt"].replace("T", " ").replace("Z", "")
                text_comm = top_comment["textDisplay"].replace("\n", "\n\t")
                author = top_comment["authorDisplayName"]
                likes = top_comment["likeCount"]
                
                main_comment = {
                    "time": time_comm,
                    "author": author,
                    "likes": likes,
                    "text": text_comm,
                    "replies": []
                }
                
                if "replies" in item:
                    for reply in item["replies"]["comments"]:
                        reply_snippet = reply["snippet"]
                        time_reply_comm = reply_snippet["publishedAt"].replace("T", " ").replace("Z", "")
                        text_reply_comm = reply_snippet["textDisplay"].replace("\n", "\n\t\t").replace("@@", "@")
                        author_reply = reply_snippet["authorDisplayName"]
                        likes_reply = reply_snippet["likeCount"]
                        
                        main_comment["replies"].append({
                            "time": time_reply_comm,
                            "author": author_reply,
                            "likes": likes_reply,
                            "text": text_reply_comm
                        })
                
                comments_data.append(main_comment)
                total_fetched += 1
                
                if total_fetched >= max_results:
                    break
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
            
            time.sleep(0.2)
            retry_count = 0
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ YouTube API error: {error_msg}")
            
            if "400" in error_msg or "processingFailure" in error_msg:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = retry_count * 2
                    print(f"🔄 Retry {retry_count}/{max_retries} in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Max retries reached. Returning {len(comments_data)} comments.")
                    break
            else:
                print(f"❌ Fatal error: {error_msg}")
                break
    
    return comments_data


def get_video_comments_adaptive(video_id: str, url: str):
    """URL ga qarab Shorts yoki oddiy video kommentarlarini olish"""
    if is_shorts_url(url):
        return get_video_comments_shorts_safe(video_id, max_results=1000)
    else:
        return get_video_comments(video_id)
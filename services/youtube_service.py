import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config

config = Config()
youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def extract_video_id(url):
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


def get_video_comments(video_id):

    comments_data = []
    next_page_token = None
    
    while True:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=100,
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
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        
        time.sleep(0.1)
    
    return comments_data


def save_comments_to_file(comments_data, file_path):

    with open(file_path, "w", encoding="utf-8") as f:
        for comment in comments_data:
            f.write(f"[{comment['time']}] ({comment['author']}, {comment['likes']} likes) {comment['text']}\n")
            if comment["replies"]:
                f.write("{\n")
                for reply in comment["replies"]:
                    f.write(f"\t[{reply['time']}] ({reply['author']}, {reply['likes']} likes) {reply['text']}\n")
                f.write("}\n")
            f.write("\n\n")


def get_comments_file_path(video_id):
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%d.%m.%Y-%H.%M.%S')
    file_path = results_dir / f"{video_id}_{timestamp}.txt"
    return str(file_path)


def get_video_comments_count(video_url: str) -> int:

    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise ValueError("❌ Noto'g'ri video URL")

    response = youtube.videos().list(
        part="statistics",
        id=video_id
    ).execute()

    if not response["items"]:
        raise ValueError("❌ Video topilmadi")

    stats = response["items"][0]["statistics"]
    comment_count = int(stats.get("commentCount", 0))

    return comment_count


def parse_timestamps(description: str) -> List[Dict[str, str]]:

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

    if not timestamps:
        return ""
    
    output = "\n\n=== VIDEO PERESKAZKA (TIMESTAMPS) ===\n\n"
    for idx, ts in enumerate(timestamps, 1):
        output += f"{idx}. {ts['time']} - {ts['title']}\n"
    
    return output


def extract_channel_id_from_url(channel_url: str) -> Optional[str]:

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
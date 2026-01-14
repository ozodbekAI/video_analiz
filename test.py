import asyncio
import re
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from config import Config

config = Config()


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?\n]+)",
        r"(?:www\.)?youtube\.com\/watch\?.*v=([^&?\n]+)",
        r"(?:www\.)?youtu\.be\/([^&?\n]+)",
        r"(?:www\.)?youtube\.com\/embed\/([^&?\n]+)"
    ]
    
    url_without_https = url.replace("https://", "").replace("http://", "")
    
    for pattern in patterns:
        match = re.search(pattern, url_without_https)
        if match:
            video_id = match.group(1)
            for char in ("?", "&", "/"):
                if char in video_id:
                    video_id = video_id.split(char)[0]
            return video_id
    
    raise ValueError("Invalid YouTube URL")


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
        
        youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        request = youtube.videos().list(
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
        
        youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
        
        request = youtube.videos().list(
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
        raise Exception(f"Video ma'lumotlarini olishda xatolik: {str(e)}")


def format_timestamps_output(timestamps: List[Dict[str, str]]) -> str:
    if not timestamps:
        return "❌ Timestamps topilmadi"
    
    output = "📋 Vaqt kodlari:\n\n"
    for idx, ts in enumerate(timestamps, 1):
        output += f"{idx}. {ts['time']} - {ts['title']}\n"
    
    return output



async def test_real_youtube_video():
    test_url = input("YouTube Video URL kiriting: ").strip()
    
    if not test_url:
        print("❌ URL kiritilmadi, test o'tkazib yuborildi")
        return
    
    try:
        result = await get_video_timestamps(test_url)
        
        print(f"\n📹 Video ID: {result['video_id']}")
        print(f"📝 Title: {result['title']}")
        no_ts = "❌ Yo'q"
        print(f"🕐 Timestamps mavjud: {'✅ Ha' if result['has_timestamps'] else no_ts}")
        print(f"📊 Timestamps soni: {result['timestamps_count']}")
        
        if result['has_timestamps']:
            print("\n" + format_timestamps_output(result['timestamps']))
        else:
            print("\n❌ Bu videoda timestamps topilmadi")
            print("\n📄 Video Description (birinchi 500 belgi):")
            print(result['description'][:500] + "...")
            
    except Exception as e:
        print(f"❌ Xatolik: {e}")



    

async def test_description_fetch():
    
    test_url = input("YouTube Video URL kiriting: ").strip()
    
    if not test_url:
        print("❌ URL kiritilmadi")
        return
    
    try:
        description = await get_video_description(test_url)
        
        print(f"\n✅ Description olindi ({len(description)} belgi)")
        print("\n📄 Description (birinchi 1000 belgi):")
        print("-" * 60)
        print(description[:1000])
        if len(description) > 1000:
            print("...")
        print("-" * 60)
        
        timestamps = parse_timestamps(description)
        if timestamps:
            print(f"\n✅ {len(timestamps)} ta timestamp topildi")
        else:
            print("\n❌ Timestamps topilmadi")
            
    except Exception as e:
        print(f"❌ Xatolik: {e}")


async def main():
    await test_real_youtube_video()
        


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Dastur to'xtatildi")
    except Exception as e:
        print(f"\n❌ Kutilmagan xatolik: {e}")

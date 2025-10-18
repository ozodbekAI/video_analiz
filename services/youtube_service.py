import re
import time
import sys
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build
from config import Config

config = Config()
youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

def extract_video_id(url):
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
            main_comment = {
                "time": time_comm,
                "text": text_comm,
                "replies": []
            }
            
            if "replies" in item:
                for reply in item["replies"]["comments"]:
                    reply_snippet = reply["snippet"]
                    time_reply_comm = reply_snippet["publishedAt"].replace("T", " ").replace("Z", "")
                    text_reply_comm = reply_snippet["textDisplay"].replace("\n", "\n\t\t").replace("@@", "@")
                    main_comment["replies"].append({
                        "time": time_reply_comm,
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
            f.write(f"[{comment['time']}] {comment['text']}\n")
            if comment["replies"]:
                f.write("{\n")
                for reply in comment["replies"]:
                    f.write(f"\t[{reply['time']}] {reply['text']}\n")
                f.write("}\n")
            f.write("\n\n")

def get_comments_file_path(video_id):
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%d.%m.%Y-%H.%M.%S')
    file_path = results_dir / f"{video_id}_{timestamp}.txt"
    return str(file_path)
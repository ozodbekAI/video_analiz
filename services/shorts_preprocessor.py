import re
from typing import List, Dict, Any
from collections import Counter


class RawDataShortsPreprocessor:
    def __init__(self):
        self.dangerous_noise_patterns = [
            r'http[s]?://\S+', 
            r'@\w+\s+@\w+\s+@\w+', 
            r'(?:подпишись|subscribe|подписывайся|подписка).*?(?:канал|channel|ютуб|youtube)',  
            r'^[\.\,\-\s\*\_\~\`]{3,}$',  
            r'^\s*$',  
            r'(?:t\.me|telegram|discord|vk\.com|inst)',  
            r'(?:купи|продаю|реклама|promotion|sale)',  
        ]

        self.preserved_emotional_patterns = [
            r'^[❤️😍🔥🥰🤩😘👍💕💖✨🎉😂😭🙏]{1,15}$',  
            r'^[\!❤️😍🔥]{1,7}$',  
            r'^[а-яa-zА-ЯA-Z]+[\!]{1,3}$',  
            r'^(?:ха|xa|ha|lol|haha|хаха){2,5}[\!]*$',  
        ]

        self.min_meaningful_length = 2 
    
    def is_dangerous_noise(self, text: str) -> bool:
        text_lower = text.lower()
        
        for pattern in self.dangerous_noise_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def is_preserved_emotional(self, text: str) -> bool:
        for pattern in self.preserved_emotional_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        return False
    
    def should_keep_comment(self, text: str) -> bool:
        if not text or len(text.strip()) == 0:
            return False
        
        if self.is_dangerous_noise(text):
            return False

        if self.is_preserved_emotional(text.strip()):
            return True
        
        meaningful_text = re.sub(r'[^\w\s]', '', text) 
        return len(meaningful_text.strip()) >= self.min_meaningful_length
    
    def clean_comments(self, raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned_comments = []
        removed_stats = Counter({
            'noise_removed': 0,
            'spam_removed': 0,
            'empty_removed': 0,
            'short_removed': 0
        })
        
        for comment in raw_comments:
            text = comment.get('text', '')
            
            if not text or len(text.strip()) == 0:
                removed_stats['empty_removed'] += 1
                continue
            
            if self.is_dangerous_noise(text):
                removed_stats['spam_removed'] += 1
                continue
            
            if not self.is_preserved_emotional(text.strip()):
                meaningful = re.sub(r'[^\w\s]', '', text)
                if len(meaningful.strip()) < self.min_meaningful_length:
                    removed_stats['short_removed'] += 1
                    continue
            
            cleaned_comments.append(comment)

        
        return cleaned_comments
    
    def get_cleaning_report(self, raw_count: int, cleaned_count: int) -> str:
        """Tozalash hisoboti (PDF uchun)"""
        removed = raw_count - cleaned_count
        efficiency = (cleaned_count / raw_count * 100) if raw_count > 0 else 0
        
        return f"""
## 🧹 Preprocessing Report

- **Original Comments:** {raw_count}
- **Cleaned Comments:** {cleaned_count}
- **Removed Noise:** {removed}
- **Efficiency:** {efficiency:.1f}%

Removed:
- Spam/Ads
- Empty comments
- URLs and external links
- Very short meaningless text
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube Parser - Гибридная версия с поддержкой Shorts"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from youtube_api import YouTubeAPI
from data_models import ParsingResult
from utils import extract_video_id, validate_video_id, create_results_dir, get_unique_filename, format_number, format_duration, log_errors
import settings


class YouTubeParser:
    """Основной класс парсера с поддержкой Shorts"""
    
    def __init__(self):
        self.api = YouTubeAPI()
        self.results_dir = create_results_dir()
    
    @log_errors
    def parse_video(self, video_id: str, video_type: str = "video", max_comments: int = 0) -> Optional[ParsingResult]:
        """Парсинг видео или Shorts"""
        print(f"\n{'='*60}")
        
        if video_type == "shorts":
            print(f"🎬 Обработка SHORTS: {video_id}")
        else:
            print(f"🎬 Обработка ВИДЕО: {video_id}")
        
        print(f"{'='*60}")
        
        # Валидация ID
        if not validate_video_id(video_id):
            print(f"❌ Некорректный ID видео: {video_id}")
            return None
        
        # Получение информации о видео
        print(f"📹 Получение информации...")
        video_info = self.api.get_video_info(video_id, video_type)
        
        if not video_info:
            print(f"❌ Не удалось получить информацию")
            return None
        
        print(f"   📝 Название: {video_info.title[:80]}..." if len(video_info.title) > 80 else f"   📝 Название: {video_info.title}")
        print(f"   📺 Канал: {video_info.channel_title}")
        print(f"   👁 Просмотров: {format_number(video_info.view_count)}")
        print(f"   ❤️ Лайков: {format_number(video_info.like_count)}")
        print(f"   💬 Комментариев по API: {format_number(video_info.comment_count)}")
        print(f"   ⏱ Длительность: {video_info.duration}")
        
        if video_info.is_shorts or video_info.duration_seconds <= 60:
            print(f"   🎯 Тип: YouTube Shorts")
        
        # Определяем, сколько комментариев собирать
        if max_comments <= 0:
            max_to_collect = min(video_info.comment_count, 10000)
        else:
            max_to_collect = min(max_comments, video_info.comment_count)
        
        # Получение комментариев
        comments = self.api.get_video_comments(video_id, video_type, max_to_collect)
        
        if not comments:
            print(f"   ℹ️  Комментарии не найдены")
            comments = []
        else:
            print(f"   💬 Найдено комментариев: {format_number(len(comments))}")
        
        # Расчет статистики
        print(f"📊 Расчет статистики...")
        from utils import StatisticsCalculator
        statistics = StatisticsCalculator.calculate_video_stats(video_info, comments, video_type)
        
        return ParsingResult(
            video=video_info,
            comments=comments,
            statistics=statistics,
            metadata={
                'video_id': video_id,
                'video_type': video_type,
                'api_requests': self.api.request_count,
                'parsing_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'comments_collected': len(comments),
                'comments_total': video_info.comment_count,
                'collection_ratio': f"{len(comments)}/{video_info.comment_count} ({len(comments)/video_info.comment_count*100:.1f}%)" if video_info.comment_count > 0 else "N/A"
            }
        )
    
    @log_errors
    def save_enriched_txt(self, result: ParsingResult) -> Optional[Path]:
        """Сохранение в обогащенном TXT формате"""
        if not result:
            return None
        
        video = result.video
        stats = result.statistics
        metadata = result.metadata
        
        filename = get_unique_filename(video.id, video.video_type, "txt")
        
        with open(filename, 'w', encoding=settings.ENCODING) as f:
            f.write("=" * 80 + "\n")
            
            if video.is_shorts:
                f.write("🎬 YouTube SHORTS ANALYSIS REPORT\n")
            else:
                f.write("📹 YouTube VIDEO ANALYSIS REPORT\n")
            
            f.write("=" * 80 + "\n\n")
            
            # Основная информация
            f.write("📋 ОСНОВНАЯ ИНФОРМАЦИЯ\n")
            f.write("-" * 40 + "\n")
            f.write(f"Тип контента: {'YouTube Shorts' if video.is_shorts else 'Обычное видео'}\n")
            f.write(f"Название: {video.title}\n")
            f.write(f"Канал: {video.channel_title}\n")
            f.write(f"Опубликовано: {video.published_at}\n")
            f.write(f"Просмотров: {format_number(video.view_count)}\n")
            f.write(f"Лайков: {format_number(video.like_count)}\n")
            f.write(f"Комментариев (по API): {format_number(video.comment_count)}\n")
            f.write(f"Длительность: {video.duration}\n")
            f.write("\n")
            
            # Статистика
            f.write("📈 СТАТИСТИКА ВИДЕО\n")
            f.write("-" * 40 + "\n")
            video_stats = stats['video_info']
            f.write(f"Вовлеченность (engagement rate): {video_stats['engagement_rate']:.2f}%\n\n")
            
            comment_stats = stats['comment_statistics']
            f.write("💬 СТАТИСТИКА КОММЕНТАРИЕВ\n")
            f.write("-" * 40 + "\n")
            f.write(f"Всего комментариев: {format_number(comment_stats['total_comments'])}\n")
            f.write(f"Основных комментариев: {format_number(comment_stats['total_top_level'])}\n")
            f.write(f"Ответов: {format_number(comment_stats['total_replies'])}\n")
            f.write(f"Уникальных авторов: {format_number(comment_stats['unique_authors'])}\n")
            f.write(f"Всего лайков на комментариях: {format_number(comment_stats['total_likes'])}\n")
            f.write(f"Среднее лайков на комментарий: {comment_stats['avg_likes_per_comment']:.2f}\n\n")
            
            # Самый популярный комментарий
            if comment_stats.get('most_liked_comment'):
                mlc = comment_stats['most_liked_comment']
                f.write("⭐ САМЫЙ ПОПУЛЯРНЫЙ КОММЕНТАРИЙ\n")
                f.write("-" * 40 + "\n")
                f.write(f"Автор: {mlc['author']}\n")
                f.write(f"Лайков: {mlc['likes']}\n")
                f.write(f"Текст: {mlc['text']}\n\n")
            
            # Комментарии
            f.write("=" * 80 + "\n\n")
            f.write("💭 КОММЕНТАРИИ\n")
            f.write("=" * 80 + "\n\n")
            
            if not result.comments:
                f.write("(Комментарии отсутствуют)\n")
            else:
                for idx, comment in enumerate(result.comments[:100], 1):  # Ограничиваем 100 для файла
                    f.write(f"\n{idx}. {comment.author}\n")
                    f.write(f"   ❤️ {comment.like_count} лайков\n")
                    f.write(f"   📅 {comment.published_at}\n")
                    f.write(f"   💬 {comment.text_clean[:200]}...\n" if len(comment.text_clean) > 200 else f"   💬 {comment.text_clean}\n")
            
            # Футер
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write(f"📅 Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"🔢 API запросов выполнено: {self.api.request_count}\n")
            f.write(f"🎯 Тип контента: {'YouTube Shorts' if video.is_shorts else 'Обычное видео'}\n")
            f.write("=" * 80 + "\n")
        
        print(f"💾 Обогащенный TXT сохранен: {filename.name}")
        return filename
    
    @log_errors
    def parse_from_file(self, filepath: str = None, max_comments_per_video: int = 0) -> List[ParsingResult]:
        """Парсинг видео из файла"""
        filepath = filepath or settings.URLS_FILE
        results = []
        
        try:
            if not Path(filepath).exists():
                print(f"❌ Файл {filepath} не найден")
                return results
            
            with open(filepath, 'r', encoding=settings.ENCODING) as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not urls:
                print(f"❌ В файле {filepath} нет URL'ов")
                return results
            
            print(f"\n🚀 Парсинг {len(urls)} видео из файла...")
            
            for idx, url in enumerate(urls, 1):
                print(f"\n[{idx}/{len(urls)}] Обработка URL: {url}")
                
                video_id, video_type = extract_video_id(url)
                
                if not video_id:
                    print(f"❌ Не удалось извлечь ID из URL: {url}")
                    continue
                
                if not validate_video_id(video_id):
                    print(f"⚠️  ID выглядит некорректным: {video_id}")
                    continue
                
                result = self.parse_video(video_id, video_type, max_comments_per_video)
                if result:
                    self.save_enriched_txt(result)
                    results.append(result)
                    time.sleep(2)  # Задержка между видео
            
            print(f"\n✅ Парсинг завершен. Обработано {len(results)} видео")
            
        except FileNotFoundError:
            print(f"❌ Файл {filepath} не найден")
        except Exception as e:
            print(f"❌ Ошибка при парсинге файла: {e}")
        
        return results


def main():
    """Точка входа"""
    parser = YouTubeParser()
    
    if len(sys.argv) > 1:
        # Режим одного видео
        url = sys.argv[1]
        
        video_id, video_type = extract_video_id(url)
        
        if not video_id:
            print(f"❌ Не удалось извлечь ID из URL: {url}")
            return
        
        if not validate_video_id(video_id):
            print(f"⚠️  ID выглядит некорректным: {video_id}")
            response = input("   Продолжить? (y/n): ")
            if response.lower() != 'y':
                return
        
        max_comments = 0
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            max_comments = int(sys.argv[2])
        
        result = parser.parse_video(video_id, video_type, max_comments)
        if result:
            parser.save_enriched_txt(result)
    else:
        # Режим обработки файла
        parser.parse_from_file()


if __name__ == "__main__":
    main()

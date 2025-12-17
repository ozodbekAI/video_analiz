import asyncio
import json
import re
from typing import List, Dict, Tuple
from database.crud import get_prompts
from services.ai_service import analyze_comments_with_prompt
import numpy as np
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IdeaEvaluation:
    idea: str
    scores: Dict[str, float]  # критерий -> оценка
    feedback: str
    ai_type: str  # creative/analytical/practical


@dataclass
class OptimizedIdea:
    original_idea: str
    optimized_idea: str
    iteration: int
    final_score: float
    confidence: float  # Достоверность оценки (0-1)
    evaluation_history: List[IdeaEvaluation]


class AdvancedIterativeIdeasOptimizer:
    def __init__(self):
        self.evaluation_criteria = {
            "engagement": {"weight": 0.25, "min": 1, "max": 10},
            "viral_potential": {"weight": 0.20, "min": 1, "max": 10},
            "uniqueness": {"weight": 0.15, "min": 1, "max": 10},
            "production_cost": {"weight": 0.15, "min": 1, "max": 10, "inverted": True},
            "audience_fit": {"weight": 0.15, "min": 1, "max": 10},
            "trend_relevance": {"weight": 0.10, "min": 1, "max": 10}
        }
        
        self.ai_weights = {
            "creative_ai": 0.35,
            "analytical_ai": 0.35, 
            "practical_ai": 0.30
        }
        
        # Конфигурация парсинга
        self.parsing_config = {
            "engagement": ["engagement", "вовлеченность", "involvement", "involucramiento"],
            "viral_potential": ["viral", "виральный", "viralidad", "sharable"],
            "uniqueness": ["uniqueness", "уникальность", "unicidad", "originality"],
            "production_cost": ["production", "стоимость", "costo", "cost", "ресурсы"],
            "audience_fit": ["audience", "аудитория", "audiencia", "publico"],
            "trend_relevance": ["trend", "тренд", "tendencia", "relevancia"]
        }

    def advanced_parse_evaluation_score(self, text: str) -> Dict[str, float]:
        """Улучшенный парсинг с несколькими стратегиями"""
        scores = {}
        text_lower = text.lower()
        
        # Стратегия 1: Поиск по ключевым словам с контекстом
        for criterion, keywords in self.parsing_config.items():
            score = self.extract_score_by_keywords(text_lower, keywords)
            if score is not None:
                scores[criterion] = score
                continue
                
        # Стратегия 2: Поиск структурированных данных (таблицы, списки)
        structured_scores = self.parse_structured_evaluation(text_lower)
        scores.update(structured_scores)
        
        # Стратегия 3: Анализ тональности и численных упоминаний
        if len(scores) < 3:  # Если мало оценок найдено
            sentiment_scores = self.extract_scores_from_sentiment(text_lower)
            scores.update(sentiment_scores)
        
        # Стратегия 4: Заполнение пропусков умным средним
        scores = self.fill_missing_scores(scores, text_lower)
        
        # Валидация и нормализация
        scores = self.validate_and_normalize_scores(scores)
        
        return scores

    def extract_score_by_keywords(self, text: str, keywords: list) -> float:
        """Извлекает оценку по ключевым словам с контекстом"""
        for keyword in keywords:
            # Ищем паттерны типа "вовлеченность: 8", "engagement 9/10"
            patterns = [
                rf'{keyword}[:\s]*(\d{{1,2}})[\s/]*\d*',  # keyword: 8 или keyword 8/10
                rf'(\d{{1,2}})[\s/]*\d*\s*{keyword}',     # 8 keyword или 8/10 keyword
                rf'{keyword}.*?(\d{{1,2}})/10',           # keyword ... 8/10
                rf'(\d{{1,2}})\s*из\s*10.*?{keyword}',    # 8 из 10 ... keyword
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    score = float(matches[0])
                    if 1 <= score <= 10:
                        return score
        
        return None

    def parse_structured_evaluation(self, text: str) -> Dict[str, float]:
        """Парсит структурированные оценки (таблицы, списки)"""
        scores = {}
        
        # Поиск табличного формата
        table_patterns = [
            r'(\w+)[:\s]*(\d+)/10',  # engagement: 8/10
            r'(\w+)[:\s]*(\d+)\s*балл',  # engagement: 8 баллов
            r'(\w+)\s*-\s*(\d+)',    # engagement - 8
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                criterion_en, score_str = match
                criterion = self.map_criterion(criterion_en)
                if criterion and score_str.isdigit():
                    score = float(score_str)
                    if 1 <= score <= 10:
                        scores[criterion] = score
        
        return scores

    def extract_scores_from_sentiment(self, text: str) -> Dict[str, float]:
        """Извлекает оценки на основе тональности текста"""
        scores = {}
        
        # Анализ эмоциональных маркеров
        sentiment_indicators = {
            "high": ["отлично", "превосходно", "великолепно", "высокий", "сильный", "9", "10", "отличная", "прекрасная"],
            "medium": ["хорошо", "нормально", "средний", "умеренный", "6", "7", "8", "хорошая", "нормальная"],
            "low": ["плохо", "слабо", "низкий", "слабый", "1", "2", "3", "4", "5", "плохая", "слабая"]
        }
        
        text_words = set(text.lower().split())
        
        for criterion in self.evaluation_criteria:
            # Ищем упоминания критерия в тексте
            criterion_mentioned = any(
                keyword in text for keyword in self.parsing_config[criterion]
            )
            
            if criterion_mentioned:
                # Оцениваем тональность упоминания
                if any(word in text_words for word in sentiment_indicators["high"]):
                    scores[criterion] = 8.5
                elif any(word in text_words for word in sentiment_indicators["medium"]):
                    scores[criterion] = 6.5
                elif any(word in text_words for word in sentiment_indicators["low"]):
                    scores[criterion] = 4.0
                else:
                    scores[criterion] = 6.0  # Нейтральная оценка по умолчанию
        
        return scores

    def fill_missing_scores(self, scores: Dict[str, float], text: str) -> Dict[str, float]:
        """Умное заполнение пропущенных оценок"""
        filled_scores = scores.copy()
        
        # Если есть хотя бы одна оценка, используем ее как базовую
        if scores:
            base_score = np.mean(list(scores.values()))
        else:
            # Анализ общего тона текста
            base_score = self.estimate_base_score_from_text(text)
        
        # Заполняем пропущенные критерии
        for criterion in self.evaluation_criteria:
            if criterion not in filled_scores:
                # Немного варьируем оценку для разных критериев
                variation = np.random.normal(0, 0.5)  # небольшой случайный разброс
                filled_scores[criterion] = max(1, min(10, base_score + variation))
        
        return filled_scores

    def estimate_base_score_from_text(self, text: str) -> float:
        """Оценивает базовую оценку на основе общего тона текста"""
        positive_words = ["отлично", "хорошо", "рекомендую", "успеш", "интересн", "перспектив"]
        negative_words = ["плохо", "слабо", "не рекомендую", "риск", "проблем", "сложн"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 7.5
        elif negative_count > positive_count:
            return 4.5
        else:
            return 6.0

    def validate_and_normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Валидация и нормализация оценок"""
        validated_scores = {}
        
        for criterion, score in scores.items():
            # Ограничиваем диапазон
            normalized_score = max(1, min(10, score))
            
            # Для стоимости производства инвертируем шкалу
            if criterion == "production_cost" and self.evaluation_criteria[criterion].get("inverted", False):
                normalized_score = 11 - normalized_score  # 1 становится 10, 10 становится 1
            
            validated_scores[criterion] = normalized_score
        
        return validated_scores

    def map_criterion(self, criterion_en: str) -> str:
        """Сопоставляет английские названия критериев с системными"""
        mapping = {
            "engagement": "engagement",
            "involvement": "engagement",
            "viral": "viral_potential", 
            "sharable": "viral_potential",
            "uniqueness": "uniqueness",
            "originality": "uniqueness",
            "production": "production_cost",
            "cost": "production_cost",
            "audience": "audience_fit",
            "trend": "trend_relevance",
            "relevance": "trend_relevance"
        }
        return mapping.get(criterion_en.lower())

    def calculate_confidence_score(self, evaluations: List[IdeaEvaluation]) -> float:
        """Рассчитывает оценку достоверности результата"""
        confidence_factors = []
        
        for evaluation in evaluations:
            # Фактор 1: Количество найденных оценок
            found_scores = len([v for v in evaluation.scores.values() if v != 6.0])  # 6.0 - оценка по умолчанию
            score_completeness = found_scores / len(self.evaluation_criteria)
            
            # Фактор 2: Разброс оценок между AI (чем больше согласие, тем выше достоверность)
            if len(evaluations) > 1:
                other_scores = [e.final_score for e in evaluations if e != evaluation]
                agreement = 1 - (abs(evaluation.final_score - np.mean(other_scores)) / 10)
            else:
                agreement = 0.7  # Консервативная оценка для одного AI
            
            # Фактор 3: Длина и детализация фидбэка
            feedback_quality = min(1.0, len(evaluation.feedback) / 500)  # Нормализуем по длине
            
            ai_confidence = (score_completeness * 0.4 + agreement * 0.4 + feedback_quality * 0.2)
            confidence_factors.append(ai_confidence)
        
        return np.mean(confidence_factors) if confidence_factors else 0.5

    def calculate_final_score(self, evaluations: List[IdeaEvaluation]) -> Tuple[float, float]:
        """Вычисляет итоговый балл и достоверность"""
        weighted_scores = []
        
        for evaluation in evaluations:
            ai_weight = self.ai_weights.get(evaluation.ai_type, 1.0)
            
            for criterion, config in self.evaluation_criteria.items():
                criterion_score = evaluation.scores.get(criterion, 5.0)
                weighted_scores.append(criterion_score * config["weight"] * ai_weight)
        
        final_score = np.mean(weighted_scores) if weighted_scores else 0
        confidence = self.calculate_confidence_score(evaluations)
        
        return final_score, confidence

    async def evaluate_with_ai(self, idea: str, ai_type: str, prompt_text: str) -> IdeaEvaluation:
        """Оценивает идею с помощью конкретного AI"""
        try:
            # Форматируем промпт с идеей
            formatted_prompt = prompt_text.format(idea=idea)
            
            # Получаем оценку от AI
            evaluation_text = await analyze_comments_with_prompt(idea, formatted_prompt)
            
            # Парсим оценки с улучшенным алгоритмом
            scores = self.advanced_parse_evaluation_score(evaluation_text)
            
            return IdeaEvaluation(
                idea=idea,
                scores=scores,
                feedback=evaluation_text,
                ai_type=ai_type
            )
        except Exception as e:
            # Возвращаем оценку по умолчанию в случае ошибки
            return IdeaEvaluation(
                idea=idea,
                scores={criterion: 5.0 for criterion in self.evaluation_criteria},
                feedback=f"Ошибка оценки: {str(e)}",
                ai_type=ai_type
            )

    async def optimize_idea_iteration(self, idea: str, iteration: int, prompts: Dict) -> OptimizedIdea:
        """Выполняет одну итерацию оптимизации идеи"""
        print(f"🚀 Итерация {iteration} для идеи: {idea[:50]}...")
        
        # Параллельная оценка тремя AI
        evaluation_tasks = [
            self.evaluate_with_ai(idea, "creative_ai", prompts['evaluator_creative']),
            self.evaluate_with_ai(idea, "analytical_ai", prompts['evaluator_analytical']),
            self.evaluate_with_ai(idea, "practical_ai", prompts['evaluator_practical'])
        ]
        
        evaluations = await asyncio.gather(*evaluation_tasks)
        
        # Вычисляем общий балл и достоверность
        final_score, confidence = self.calculate_final_score(evaluations)
        
        # Собираем все фидбэки для улучшения
        all_feedback = "\n\n".join([
            f"👁🗨 {eval.ai_type}:\n{eval.feedback}" 
            for eval in evaluations
        ])
        
        # Улучшаем идею на основе фидбэков
        improvement_prompt = prompts['improver'].format(
            idea=idea,
            feedback=all_feedback,
            iteration=iteration,
            current_score=final_score
        )
        
        optimized_idea_text = await analyze_comments_with_prompt(idea, improvement_prompt)
        
        return OptimizedIdea(
            original_idea=idea,
            optimized_idea=optimized_idea_text,
            iteration=iteration,
            final_score=final_score,
            confidence=confidence,
            evaluation_history=evaluations
        )

    async def run_optimization_pipeline(self, initial_ideas: List[str], prompts: Dict, max_iterations: int = 3) -> List[OptimizedIdea]:
        """Запускает полный pipeline оптимизации"""
        optimized_ideas = []
        
        for i, idea in enumerate(initial_ideas):
            print(f"🔍 Обработка идеи {i+1}/{len(initial_ideas)}")
            
            current_idea = idea
            best_idea = None
            best_score = 0
            
            for iteration in range(1, max_iterations + 1):
                # Оптимизируем на текущей итерации
                optimized = await self.optimize_idea_iteration(current_idea, iteration, prompts)
                
                # Сохраняем лучшую версию
                if optimized.final_score > best_score:
                    best_idea = optimized
                    best_score = optimized.final_score
                
                # Для следующей итерации используем оптимизированную версию
                current_idea = optimized.optimized_idea
                
                print(f"  ✅ Итерация {iteration}: оценка {optimized.final_score:.2f}, достоверность {optimized.confidence:.2f}")
            
            if best_idea:
                optimized_ideas.append(best_idea)
        
        # Сортируем по итоговому баллу
        optimized_ideas.sort(key=lambda x: x.final_score, reverse=True)
        
        return optimized_ideas

    def generate_optimization_report(self, optimized_ideas: List[OptimizedIdea]) -> str:
        """Генерирует детальный отчет по оптимизации"""
        report = "🧠 <b>ОТЧЕТ ПО ИТЕРАТИВНОЙ ОПТИМИЗАЦИИ ИДЕЙ</b>\n\n"
        report += f"📊 Всего идей: {len(optimized_ideas)}\n"
        report += f"🕐 Время анализа: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        for i, idea in enumerate(optimized_ideas[:5], 1):  # Топ-5 идей
            report += f"🏆 <b>ИДЕЯ #{i} (Оценка: {idea.final_score:.2f}/10, Достоверность: {idea.confidence*100:.1f}%)</b>\n"
            report += f"🔄 Итераций: {idea.iteration}\n\n"
            
            report += f"💡 <b>Финальная версия:</b>\n{idea.optimized_idea}\n\n"
            
            # Детали оценок
            report += "📈 <b>Детальная оценка:</b>\n"
            for criterion, config in self.evaluation_criteria.items():
                avg_score = np.mean([eval.scores.get(criterion, 5) for eval in idea.evaluation_history])
                report += f"  • {criterion}: {avg_score:.1f}/10 (вес: {config['weight']*100}%)\n"
            
            report += "\n" + "="*50 + "\n\n"
        
        return report


# Глобальный экземпляр улучшенного оптимизатора
optimizer = AdvancedIterativeIdeasOptimizer()
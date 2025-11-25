import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Результат валидации одного модуля"""
    is_valid: bool
    quality_score: float
    errors: List[str]
    warnings: List[str]
    metrics: Dict
    retry_needed: bool

class AdvancedModuleValidator:
    """Улучшенный валидатор с более гибкими критериями"""
    
    def __init__(self):
        self.modules_config = {
            "10-1": {
                "name": "Контент-Детектив",
                "critical_sections": ["МЕТА-ИНФОРМАЦИЯ", "ТАБЛИЦА"],
                "required_headers": ["ThemeID", "Тема", "Mentions"],
                # Более гибкий паттерн ID
                "id_pattern": r'\[([^\]]+→[^\]]+→[^\]]+|[A-Za-z0-9_\-]+)\]',
                # Упрощенный паттерн таблицы
                "table_pattern": r'(ThemeID|ID).*?(Тема|Название).*?(Mentions|Упоминания)',
                "min_entities": 1,
                "min_quality_score": 35  # Снижен порог
            },
            "10-2": {
                "name": "Эмоциональный Кардиограф",
                "critical_sections": ["МЕТА-ИНФОРМАЦИЯ", "ТАБЛИЦА"],
                "required_headers": ["EmotionID", "триггер", "Mentions"],
                "id_pattern": r'\[([^\]]+→[^\]]+→[^\]]+|[A-Za-z0-9_\-]+)\]',
                "table_pattern": r'(EmotionID|ID).*?(триггер|Эмоция).*?(Mentions|Упоминания)',
                "min_entities": 1,
                "min_quality_score": 35
            },
            "10-3": {
                "name": "Архитектор Персон",
                "critical_sections": ["МЕТА-ИНФОРМАЦИЯ", "ТАБЛИЦА"],
                "required_headers": ["PersonaID", "Персон", "Size"],
                "id_pattern": r'\[([^\]]+→[^\]]+→[^\]]+|[A-Za-z0-9_\-]+)\]',
                "table_pattern": r'(PersonaID|ID).*?(Персон|Имя).*?(Size|Размер)',
                "min_entities": 1,
                "min_quality_score": 35
            },
            "10-4": {
                "name": "Системный Диагност",
                "critical_sections": ["МЕТА-ИНФОРМАЦИЯ", "ТАБЛИЦА"],
                "required_headers": ["ID", "Кластер", "Приоритет"],
                "id_pattern": r'\[([^\]]+→[^\]]+→[^\]]+|[A-Za-z0-9_\-]+)\]',
                "table_pattern": r'ID.*?(Кластер|Название).*?(Приоритет|Priority)',
                "min_entities": 1,
                "min_quality_score": 35
            }
        }
        
        self.max_retries = 2

    def validate_module(self, module_id: str, content: str, attempt: int = 1) -> ValidationResult:
        """Улучшенная валидация с более мягкими критериями"""
        config = self.modules_config[module_id]
        errors = []
        warnings = []
        metrics = {}
        quality_points = 0
        max_points = 100

        # 1. Проверка критических секций (30 баллов)
        section_score = 0
        sections_found = 0
        for section in config["critical_sections"]:
            # Более гибкий поиск секций
            if section.lower() in content.lower():
                sections_found += 1
                section_score += 30 / len(config["critical_sections"])
        
        quality_points += section_score
        
        if sections_found == 0:
            errors.append(f"Отсутствуют критические секции")

        # 2. Проверка структуры таблицы (25 баллов) - БОЛЕЕ ГИБКО
        if "table_pattern" in config:
            # Используем IGNORECASE и DOTALL для гибкости
            if re.search(config["table_pattern"], content, re.IGNORECASE | re.DOTALL):
                quality_points += 25
            else:
                # Даём частичные баллы если есть хоть какая-то таблица
                if re.search(r'\|\s*\w+\s*\|', content) or re.search(r'^\s*\d+\.?\s+', content, re.MULTILINE):
                    quality_points += 15
                    warnings.append("Структура таблицы не полностью соответствует шаблону")
                else:
                    warnings.append("Таблица не обнаружена")

        # 3. Проверка ID сущностей (25 баллов) - БОЛЕЕ ГИБКО
        id_matches = re.findall(config["id_pattern"], content)
        
        # Также проверяем альтернативные форматы ID
        alternative_ids = re.findall(r'(?:theme|emotion|persona|cluster)_?\d+', content, re.IGNORECASE)
        
        total_entities = len(id_matches) + len(alternative_ids)
        metrics["entities_count"] = total_entities
        
        if total_entities >= config["min_entities"]:
            # Градуированная оценка: чем больше сущностей, тем лучше
            entities_score = min(25, 10 + (total_entities * 3))
            quality_points += entities_score
        else:
            # Даём частичные баллы даже если недостаточно
            quality_points += 5
            warnings.append(f"Найдено {total_entities} сущностей (рекомендуется больше)")

        # 4. Проверка обязательных заголовков (10 баллов) - ГИБКО
        headers_found = 0
        for header in config["required_headers"]:
            # Проверяем с учётом регистра и частичного совпадения
            if header.lower() in content.lower():
                headers_found += 1
        
        header_score = (headers_found / len(config["required_headers"])) * 10
        quality_points += header_score

        # 5. Проверка мета-информации (10 баллов)
        if "МЕТА-ИНФОРМАЦИЯ" in content or "Видео ID" in content or "hash(" in content:
            quality_points += 10
        else:
            quality_points += 5  # Частичные баллы
            warnings.append("Мета-информация неполная")

        # Определяем нужен ли retry
        retry_needed = quality_points < config["min_quality_score"] and attempt < self.max_retries
        
        return ValidationResult(
            is_valid=quality_points >= config["min_quality_score"],
            quality_score=quality_points,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            retry_needed=retry_needed
        )

    def generate_retry_instructions(self, module_id: str, validation_result: ValidationResult) -> str:
        """Улучшенные инструкции для retry"""
        config = self.modules_config[module_id]
        
        instructions = f"""🔄 ТРЕБУЕТСЯ УЛУЧШЕНИЕ КАЧЕСТВА АНАЛИЗА

Модуль: {config['name']} (ID: {module_id})
Текущее качество: {validation_result.quality_score:.0f}/100
Требуется: минимум {config['min_quality_score']}

⚠️ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:
"""
        
        if validation_result.errors:
            for error in validation_result.errors:
                instructions += f"  ❌ {error}\n"
        
        if validation_result.warnings:
            instructions += "\n💡 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:\n"
            for warning in validation_result.warnings:
                instructions += f"  ⚡ {warning}\n"
        
        instructions += f"""
📋 ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ:

1. СТРУКТУРА ОТВЕТА:
   - Начать с секции "МЕТА-ИНФОРМАЦИЯ ДЛЯ АГРЕГАЦИИ"
   - Включить "СВОДНУЮ ТАБЛИЦУ" с данными
   - Завершить выводами и статусом

2. ФОРМАТ ТАБЛИЦЫ:
"""

        # Специфичные примеры для каждого модуля
        if module_id == "10-1":
            instructions += """
   ThemeID | Тема/Вопрос | Категория | Mentions | Norm_Mentions | Topic_Score | Приоритет
   [ID]    | Название    | Категория | Число    | 0.0-1.0       | Число       | Высокий/Средний/Низкий
"""
        elif module_id == "10-2":
            instructions += """
   EmotionID | Эмоциональный триггер | Эмоция | Mentions | Norm_Mentions | Emotional_Charge | Приоритет
   [ID]      | Описание             | Тип    | Число    | 0.0-1.0       | Число            | Высокий/Средний/Низкий
"""
        elif module_id == "10-3":
            instructions += """
   PersonaID | Имя Персоны | Тип | Segment_Size | Norm_Size | ИВС | Приоритет
   [ID]      | Название    | Тип | Число        | 0.0-1.0   | Число | Высокий/Средний/Низкий
"""
        elif module_id == "10-4":
            instructions += """
   ID   | Тип | Название Кластера | Категория | ИУВ | Приоритет | Срочность
   [ID] | Тип | Описание         | Категория | Число | Высокий/Средний/Низкий | Срочность
"""

        instructions += f"""
3. ФОРМАТ ID:
   ✅ Правильно: [Контент→Образование→theme_001]
   ✅ Допустимо: [theme_001] или theme_001
   ❌ Неправильно: без квадратных скобок или идентификатора

4. КОЛИЧЕСТВО СУЩНОСТЕЙ:
   Минимум: {config['min_entities']}
   Рекомендуется: 5-10 для полноценного анализа

🎯 ПОВТОРИТЕ АНАЛИЗ С УЧЁТОМ ЭТИХ ТРЕБОВАНИЙ!
"""

        return instructions

    def format_validation_report(self, module_id: str, validation_result: ValidationResult, 
                                 attempt: int) -> str:
        """Форматирование отчета для консоли"""
        config = self.modules_config[module_id]
        
        status_emoji = "✅" if validation_result.is_valid else "❌"
        
        report = f"""
{status_emoji} ВАЛИДАЦИЯ МОДУЛЯ {module_id} ({config['name']})
{'='*60}
Попытка: {attempt}/{self.max_retries + 1}
Статус: {"УСПЕШНО" if validation_result.is_valid else "ТРЕБУЕТСЯ УЛУЧШЕНИЕ"}
Качество: {validation_result.quality_score:.1f}/100 (минимум: {config['min_quality_score']})
Сущностей найдено: {validation_result.metrics.get('entities_count', 0)}
"""
        
        if validation_result.errors:
            report += f"\nОшибки:\n"
            for error in validation_result.errors:
                report += f"  ❌ {error}\n"
        
        if validation_result.warnings:
            report += f"\nПредупреждения:\n"
            for warning in validation_result.warnings:
                report += f"  ⚠️ {warning}\n"
        
        if validation_result.retry_needed:
            report += f"\n🔄 Запланирована повторная попытка\n"
        
        return report


class ValidationLogger:
    """Логгер для сохранения истории валидации"""
    
    @staticmethod
    def save_validation_log(video_id: str, module_id: str, attempt: int, 
                           validation_result: ValidationResult, 
                           retry_instructions: Optional[str] = None):
        """Сохранение лога валидации в файл"""
        import json
        from pathlib import Path
        from datetime import datetime
        
        logs_dir = Path(f"validation_logs/{video_id}")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"{module_id}_attempt{attempt}.json"
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "module_id": module_id,
            "attempt": attempt,
            "is_valid": validation_result.is_valid,
            "quality_score": validation_result.quality_score,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "metrics": validation_result.metrics,
            "retry_needed": validation_result.retry_needed,
            "retry_instructions": retry_instructions
        }
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        return str(log_file)
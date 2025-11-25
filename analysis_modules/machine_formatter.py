import json
import re
from datetime import datetime
from typing import Dict, List, Any

class MachineReadableFormatter:
    def __init__(self):
        self.version = "1.0"
    
    def create_machine_report(self, 
                            video_meta: Dict,
                            modules_data: Dict[str, str],
                            calculated_indices: Dict,
                            human_insights: List[Dict],
                            validation_report: Dict) -> str:
        """
        Создает полный машиночитаемый отчет со ВСЕМИ данными
        """
        
        # Извлекаем сущности из всех модулей
        entities = self._extract_all_entities(modules_data)
        
        machine_report = {
            "metadata": {
                "format_version": self.version,
                "report_type": "video_analysis",
                "video_id": video_meta.get("video_id"),
                "video_url": video_meta.get("video_url"),
                "video_title": video_meta.get("video_title"),
                "upload_date": video_meta.get("upload_date"),
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "analysis_timestamp": datetime.now().isoformat(),
                "comment_count": video_meta.get("comment_count"),
                "user_id": video_meta.get("user_id")
            },
            
            "strategic_indices": {
                "content_health_index": calculated_indices.get("content_health_index"),
                "audience_evolution_vector": calculated_indices.get("audience_evolution_vector"),
                "overall_priority": calculated_indices.get("overall_priority"),
                "quality_score": calculated_indices.get("quality_score"),
                "calculation_timestamp": datetime.now().isoformat()
            },
            
            "entities": entities,
            
            "cross_module_insights": human_insights,
            
            "raw_modules_data": {
                "module_10_1": modules_data.get("10-1", ""),
                "module_10_2": modules_data.get("10-2", ""),
                "module_10_3": modules_data.get("10-3", ""),
                "module_10_4": modules_data.get("10-4", "")
            },
            
            "validation": {
                "quality_index": validation_report.get("quality_index"),
                "present_modules": validation_report.get("present_modules", []),
                "missing_modules": validation_report.get("missing_modules", []),
                "warnings": validation_report.get("quality_warnings", [])
            },
            
            "aggregation_metadata": {
                "is_aggregation_ready": True,
                "required_fields_present": self._check_required_fields(entities, calculated_indices),
                "data_completeness_score": self._calculate_completeness_score(entities, human_insights),
                "next_aggregation_step": "channel_trend_analysis"
            }
        }
        
        return json.dumps(machine_report, ensure_ascii=False, indent=2)
    
    def _extract_all_entities(self, modules_data: Dict[str, str]) -> Dict[str, List]:
        """Извлекает все сущности из всех модулей"""
        return {
            "themes": self._extract_themes(modules_data.get("10-1", "")),
            "emotions": self._extract_emotions(modules_data.get("10-2", "")),
            "personas": self._extract_personas(modules_data.get("10-3", "")),
            "risks": self._extract_risks(modules_data.get("10-4", "")),
            "opportunities": self._extract_opportunities(modules_data.get("10-4", "")),
            "connections": self._extract_cross_module_connections(modules_data)
        }
    
    def _extract_themes(self, module_10_1_content: str) -> List[Dict]:
        """Извлекает темы из модуля 10-1 с улучшенным парсингом"""
        themes = []
        
        # Основной парсинг таблицы
        lines = module_10_1_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ДЛЯ СИНТЕЗА" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'ThemeID' in line:
                continue  # Пропускаем заголовок таблицы
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 8:
                    themes.append({
                        "theme_id": parts[0],
                        "name": parts[1],
                        "category": parts[2],
                        "mentions": int(parts[3]) if parts[3].isdigit() else 0,
                        "norm_mentions": float(parts[4]) if self._is_float(parts[4]) else 0.0,
                        "topic_score": int(parts[5]) if parts[5].isdigit() else 0,
                        "priority": parts[6],
                        "evolution_stage": parts[7],
                        "module_source": "10-1"
                    })
        
        # Fallback-парсинг для альтернативных форматов
        if not themes:
            themes = self._extract_themes_fallback(module_10_1_content)
        
        return themes
    
    def _extract_themes_fallback(self, module_10_1_content: str) -> List[Dict]:
        """Fallback-парсинг тем для альтернативных форматов"""
        themes = []
        
        # Fallback 1: Искать любые ThemeID в тексте
        theme_matches = re.findall(r'ThemeID[:\s]*([^\n]+)', module_10_1_content)
        for match in theme_matches:
            themes.append({
                "theme_id": match.strip(),
                "name": "Извлечено из текста", 
                "category": "unknown",
                "mentions": 1,
                "norm_mentions": 0.1,
                "topic_score": 10,
                "priority": "medium",
                "evolution_stage": "unknown",
                "module_source": "10-1_fallback"
            })
        
        # Fallback 2: Поиск по паттернам названий тем
        theme_patterns = [
            r'Тема[:\s]*([^\n]+)',
            r'Тематика[:\s]*([^\n]+)',
            r'Topic[:\s]*([^\n]+)'
        ]
        
        for pattern in theme_patterns:
            matches = re.findall(pattern, module_10_1_content, re.IGNORECASE)
            for match in matches:
                theme_name = match.strip()
                if len(theme_name) > 3:  # Фильтруем слишком короткие matches
                    themes.append({
                        "theme_id": f"fallback_{len(themes)+1}",
                        "name": theme_name,
                        "category": "extracted",
                        "mentions": 1,
                        "norm_mentions": 0.1,
                        "topic_score": 5,
                        "priority": "low",
                        "evolution_stage": "unknown",
                        "module_source": "10-1_fallback_pattern"
                    })
        
        return themes
    
    def _extract_emotions(self, module_10_2_content: str) -> List[Dict]:
        """Извлекает эмоции из модуля 10-2 с улучшенным парсингом"""
        emotions = []
        
        lines = module_10_2_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ДЛЯ СИНТЕЗА" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'EmotionID' in line:
                continue
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 9:
                    emotions.append({
                        "emotion_id": parts[0],
                        "trigger": parts[1],
                        "dominant_emotion": parts[2],
                        "mentions": int(parts[3]) if parts[3].isdigit() else 0,
                        "norm_mentions": float(parts[4]) if self._is_float(parts[4]) else 0.0,
                        "emotional_charge": float(parts[5]) if self._is_float(parts[5]) else 0.0,
                        "intensity": float(parts[6]) if self._is_float(parts[6]) else 0.0,
                        "priority": parts[7],
                        "trend": parts[8],
                        "module_source": "10-2"
                    })
        
        # Fallback-парсинг для альтернативных форматов
        if not emotions:
            emotions = self._extract_emotions_fallback(module_10_2_content)
        
        return emotions
    
    def _extract_emotions_fallback(self, module_10_2_content: str) -> List[Dict]:
        """Fallback-парсинг эмоций для альтернативных форматов"""
        emotions = []
        
        # Fallback 1: Искать EmotionID в тексте
        emotion_matches = re.findall(r'EmotionID[:\s]*([^\n]+)', module_10_2_content)
        for match in emotion_matches:
            emotions.append({
                "emotion_id": match.strip(),
                "trigger": "Извлечено из текста",
                "dominant_emotion": "unknown",
                "mentions": 1,
                "norm_mentions": 0.1,
                "emotional_charge": 0.5,
                "intensity": 0.5,
                "priority": "medium",
                "trend": "stable",
                "module_source": "10-2_fallback"
            })
        
        # Fallback 2: Поиск эмоций по ключевым словам
        emotion_patterns = [
            r'Эмоция[:\s]*([^\n]+)',
            r'Emotion[:\s]*([^\n]+)',
            r'Триггер[:\s]*([^\n]+)',
            r'Trigger[:\s]*([^\n]+)'
        ]
        
        for pattern in emotion_patterns:
            matches = re.findall(pattern, module_10_2_content, re.IGNORECASE)
            for match in matches:
                emotion_data = match.strip()
                if len(emotion_data) > 3:
                    emotions.append({
                        "emotion_id": f"emotion_fallback_{len(emotions)+1}",
                        "trigger": emotion_data,
                        "dominant_emotion": self._detect_emotion_type(emotion_data),
                        "mentions": 1,
                        "norm_mentions": 0.1,
                        "emotional_charge": 0.5,
                        "intensity": 0.5,
                        "priority": "low",
                        "trend": "unknown",
                        "module_source": "10-2_fallback_pattern"
                    })
        
        return emotions
    
    def _extract_personas(self, module_10_3_content: str) -> List[Dict]:
        """Извлекает персоны из модуля 10-3 с улучшенным парсингом"""
        personas = []
        
        lines = module_10_3_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ДЛЯ СИНТЕЗА" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'PersonaID' in line:
                continue
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 9:
                    personas.append({
                        "persona_id": parts[0],
                        "name": parts[1],
                        "type": parts[2],
                        "segment_size": int(parts[3]) if parts[3].isdigit() else 0,
                        "norm_size": int(parts[4]) if parts[4].isdigit() else 0,
                        "influence_index": float(parts[5]) if self._is_float(parts[5]) else 0.0,
                        "engagement": float(parts[6]) if self._is_float(parts[6]) else 0.0,
                        "priority": parts[7],
                        "development_stage": parts[8],
                        "module_source": "10-3"
                    })
        
        # Fallback-парсинг для альтернативных форматов
        if not personas:
            personas = self._extract_personas_fallback(module_10_3_content)
        
        return personas
    
    def _extract_personas_fallback(self, module_10_3_content: str) -> List[Dict]:
        """Fallback-парсинг персон для альтернативных форматов"""
        personas = []
        
        # Fallback 1: Искать PersonaID в тексте
        persona_matches = re.findall(r'PersonaID[:\s]*([^\n]+)', module_10_3_content)
        for match in persona_matches:
            personas.append({
                "persona_id": match.strip(),
                "name": "Извлечено из текста",
                "type": "unknown",
                "segment_size": 1,
                "norm_size": 1,
                "influence_index": 0.5,
                "engagement": 0.5,
                "priority": "medium",
                "development_stage": "unknown",
                "module_source": "10-3_fallback"
            })
        
        # Fallback 2: Поиск персон по ключевым словам
        persona_patterns = [
            r'Персона[:\s]*([^\n]+)',
            r'Persona[:\s]*([^\n]+)',
            r'Аудитория[:\s]*([^\n]+)',
            r'Audience[:\s]*([^\n]+)',
            r'Сегмент[:\s]*([^\n]+)',
            r'Segment[:\s]*([^\n]+)'
        ]
        
        for pattern in persona_patterns:
            matches = re.findall(pattern, module_10_3_content, re.IGNORECASE)
            for match in matches:
                persona_data = match.strip()
                if len(persona_data) > 3:
                    personas.append({
                        "persona_id": f"persona_fallback_{len(personas)+1}",
                        "name": persona_data,
                        "type": self._detect_persona_type(persona_data),
                        "segment_size": 1,
                        "norm_size": 1,
                        "influence_index": 0.3,
                        "engagement": 0.3,
                        "priority": "low",
                        "development_stage": "identified",
                        "module_source": "10-3_fallback_pattern"
                    })
        
        return personas
    
    def _extract_risks(self, module_10_4_content: str) -> List[Dict]:
        """Извлекает риски из модуля 10-4 с улучшенным парсингом"""
        risks = []
        
        lines = module_10_4_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ПРИОРИТЕТОВ" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'ID' in line:
                continue
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 8 and 'риск' in parts[1].lower():
                    risks.append({
                        "risk_id": parts[0],
                        "type": "risk",
                        "name": parts[2],
                        "category": parts[3],
                        "risk_index": float(parts[4]) if self._is_float(parts[4]) else 0.0,
                        "priority": parts[5],
                        "escalation_potential": parts[6],
                        "urgency": parts[7],
                        "module_source": "10-4"
                    })
        
        # Fallback-парсинг для альтернативных форматов
        if not risks:
            risks = self._extract_risks_fallback(module_10_4_content)
        
        return risks
    
    def _extract_risks_fallback(self, module_10_4_content: str) -> List[Dict]:
        """Fallback-парсинг рисков для альтернативных форматов"""
        risks = []
        
        # Fallback 1: Поиск рисков по ключевым словам
        risk_patterns = [
            r'Риск[:\s]*([^\n]+)',
            r'Risk[:\s]*([^\n]+)',
            r'Угроза[:\s]*([^\n]+)',
            r'Threat[:\s]*([^\n]+)',
            r'Проблема[:\s]*([^\n]+)',
            r'Problem[:\s]*([^\n]+)',
            r'Опасность[:\s]*([^\n]+)',
            r'Danger[:\s]*([^\n]+)'
        ]
        
        for pattern in risk_patterns:
            matches = re.findall(pattern, module_10_4_content, re.IGNORECASE)
            for match in matches:
                risk_data = match.strip()
                if len(risk_data) > 3:
                    risks.append({
                        "risk_id": f"risk_fallback_{len(risks)+1}",
                        "type": "risk",
                        "name": risk_data,
                        "category": self._detect_risk_category(risk_data),
                        "risk_index": 0.5,
                        "priority": "medium",
                        "escalation_potential": "medium",
                        "urgency": "medium",
                        "module_source": "10-4_fallback_pattern"
                    })
        
        return risks
    
    def _extract_opportunities(self, module_10_4_content: str) -> List[Dict]:
        """Извлекает возможности из модуля 10-4 с улучшенным парсингом"""
        opportunities = []
        
        lines = module_10_4_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ПРИОРИТЕТОВ" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'ID' in line:
                continue
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 8 and 'возможность' in parts[1].lower():
                    opportunities.append({
                        "opportunity_id": parts[0],
                        "type": "opportunity",
                        "name": parts[2],
                        "category": parts[3],
                        "opportunity_index": float(parts[4]) if self._is_float(parts[4]) else 0.0,
                        "priority": parts[5],
                        "realization_potential": parts[6],
                        "timeframe": parts[7],
                        "module_source": "10-4"
                    })
        
        # Fallback-парсинг для альтернативных форматов
        if not opportunities:
            opportunities = self._extract_opportunities_fallback(module_10_4_content)
        
        return opportunities
    
    def _extract_opportunities_fallback(self, module_10_4_content: str) -> List[Dict]:
        """Fallback-парсинг возможностей для альтернативных форматов"""
        opportunities = []
        
        # Fallback 1: Поиск возможностей по ключевым словам
        opportunity_patterns = [
            r'Возможность[:\s]*([^\n]+)',
            r'Opportunity[:\s]*([^\n]+)',
            r'Перспектива[:\s]*([^\n]+)',
            r'Prospect[:\s]*([^\n]+)',
            r'Потенциал[:\s]*([^\n]+)',
            r'Potential[:\s]*([^\n]+)',
            r'Шанс[:\s]*([^\n]+)',
            r'Chance[:\s]*([^\n]+)'
        ]
        
        for pattern in opportunity_patterns:
            matches = re.findall(pattern, module_10_4_content, re.IGNORECASE)
            for match in matches:
                opportunity_data = match.strip()
                if len(opportunity_data) > 3:
                    opportunities.append({
                        "opportunity_id": f"opportunity_fallback_{len(opportunities)+1}",
                        "type": "opportunity",
                        "name": opportunity_data,
                        "category": self._detect_opportunity_category(opportunity_data),
                        "opportunity_index": 0.5,
                        "priority": "medium",
                        "realization_potential": "medium",
                        "timeframe": "medium_term",
                        "module_source": "10-4_fallback_pattern"
                    })
        
        return opportunities
    
    def _extract_cross_module_connections(self, modules_data: Dict[str, str]) -> List[Dict]:
        """Извлекает межмодульные связи"""
        connections = []
        connection_patterns = ['СВЯЗЬ_10-', 'DYNAMIC_REF']
        
        for module_id, content in modules_data.items():
            lines = content.split('\n')
            for line in lines:
                for pattern in connection_patterns:
                    if pattern in line:
                        connections.append({
                            "source_module": module_id,
                            "connection_type": pattern.replace('_', '').replace('10-', ''),
                            "content": line.strip(),
                            "extracted_at": datetime.now().isoformat()
                        })
        
        return connections
    
    def _detect_emotion_type(self, text: str) -> str:
        """Определяет тип эмоции по тексту"""
        positive_emotions = ['радость', 'счастье', 'восторг', 'удовольствие', 'любовь', 'гордость', 'joy', 'happy', 'delight', 'pleasure', 'love', 'proud']
        negative_emotions = ['гнев', 'злость', 'печаль', 'грусть', 'страх', 'тревога', 'anger', 'rage', 'sadness', 'fear', 'anxiety', 'disgust']
        
        text_lower = text.lower()
        
        for emotion in positive_emotions:
            if emotion in text_lower:
                return "positive"
        
        for emotion in negative_emotions:
            if emotion in text_lower:
                return "negative"
        
        return "neutral"
    
    def _detect_persona_type(self, text: str) -> str:
        """Определяет тип персоны по тексту"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['эксперт', 'специалист', 'профессионал', 'expert', 'specialist', 'professional']):
            return "expert"
        elif any(word in text_lower for word in ['новичок', 'начинающий', 'newbie', 'beginner', 'starter']):
            return "beginner"
        elif any(word in text_lower for word in ['критик', 'скептик', 'critic', 'skeptic']):
            return "critic"
        elif any(word in text_lower for word in ['энтузиаст', 'фанат', 'enthusiast', 'fan']):
            return "enthusiast"
        
        return "general"
    
    def _detect_risk_category(self, text: str) -> str:
        """Определяет категорию риска по тексту"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['репутац', 'reputation', 'image']):
            return "reputation"
        elif any(word in text_lower for word in ['финанс', 'деньг', 'money', 'financial']):
            return "financial"
        elif any(word in text_lower for word in ['технич', 'technical', 'технолог', 'technology']):
            return "technical"
        elif any(word in text_lower for word in ['юрид', 'legal', 'правов', 'law']):
            return "legal"
        
        return "general"
    
    def _detect_opportunity_category(self, text: str) -> str:
        """Определяет категорию возможности по тексту"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['рост', 'увеличение', 'growth', 'increase']):
            return "growth"
        elif any(word in text_lower for word in ['монетизац', 'доход', 'revenue', 'monetization']):
            return "monetization"
        elif any(word in text_lower for word in ['аудитор', 'audience', 'подписчик', 'subscriber']):
            return "audience"
        elif any(word in text_lower for word in ['контент', 'content', 'видео', 'video']):
            return "content"
        
        return "general"
    
    def _check_required_fields(self, entities: Dict, indices: Dict) -> bool:
        """Проверяет наличие обязательных полей"""
        required_entities = ['themes', 'emotions', 'personas']
        required_indices = ['content_health_index', 'audience_evolution_vector']
        
        for entity in required_entities:
            if not entities.get(entity):
                return False
        
        for index in required_indices:
            if index not in indices:
                return False
        
        return True
    
    def _calculate_completeness_score(self, entities: Dict, insights: List) -> float:
        """Рассчитывает оценку полноты данных"""
        total_entities = sum(len(entity_list) for entity_list in entities.values())
        insights_count = len(insights)
        
        # Максимально ожидаемое количество сущностей (эмпирически)
        max_expected_entities = 50
        max_expected_insights = 5
        
        entity_score = min(total_entities / max_expected_entities, 1.0)
        insight_score = min(insights_count / max_expected_insights, 1.0)
        
        return round((entity_score * 0.7 + insight_score * 0.3) * 100, 1)
    
    def _is_float(self, value: str) -> bool:
        """Проверяет, можно ли преобразовать строку в float"""
        try:
            float(value)
            return True
        except ValueError:
            return False
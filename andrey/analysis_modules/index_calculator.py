from typing import Dict, List
import re

class IndexCalculator:
    def __init__(self):
        pass
    
    def calculate_all_indices(self, modules_data: Dict[str, str]) -> Dict[str, any]:
        """
        Расчет всех стратегических индексов на основе данных модулей
        """
        themes = self._extract_themes_for_calculation(modules_data.get("10-1", ""))
        emotions = self._extract_emotions_for_calculation(modules_data.get("10-2", ""))
        personas = self._extract_personas_for_calculation(modules_data.get("10-3", ""))
        risks = self._extract_risks_for_calculation(modules_data.get("10-4", ""))
        
        return {
            "content_health_index": self._calculate_content_health_index(themes, emotions, personas, risks),
            "audience_evolution_vector": self._calculate_audience_evolution_vector(personas, themes),
            "overall_priority": self._calculate_overall_priority(risks),
            "quality_score": self._calculate_quality_score(themes, emotions, personas)
        }
    
    def _extract_themes_for_calculation(self, module_10_1_content: str) -> List[Dict]:
        """Извлекает темы для расчетов"""
        themes = []
        lines = module_10_1_content.split('\n')
        in_table = False
        
        for line in lines:
            if "СВОДНАЯ ТАБЛИЦА ДЛЯ СИНТЕЗА" in line:
                in_table = True
                continue
            if in_table and line.strip().startswith('|') and 'ThemeID' in line:
                continue
            if in_table and line.strip().startswith('|') and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 6:
                    themes.append({
                        "topic_score": int(parts[5]) if parts[5].isdigit() else 0
                    })
        
        return themes
    
    def _extract_emotions_for_calculation(self, module_10_2_content: str) -> List[Dict]:
        """Извлекает эмоции для расчетов"""
        emotions = []
        lines = module_10_2_content.split('\n')
        in_table = False
        
        # Считаем позитивные эмоции
        positive_count = 0
        total_emotions = 0
        
        for line in lines:
            if "Позитив/Благодарность" in line:
                # Извлекаем процент позитивных эмоций
                match = re.search(r'(\d+)%', line)
                if match:
                    positive_count = int(match.group(1))
            if "Общее количество комментариев" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    total_emotions = int(match.group(1))
        
        return {
            "positive_ratio": positive_count / 100 if positive_count > 0 else 0.3,
            "total_emotions": total_emotions
        }
    
    def _extract_personas_for_calculation(self, module_10_3_content: str) -> List[Dict]:
        """Извлекает персоны для расчетов"""
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
                if len(parts) >= 6:
                    personas.append({
                        "influence_index": float(parts[5]) if self._is_float(parts[5]) else 0.0
                    })
        
        return personas
    
    def _extract_risks_for_calculation(self, module_10_4_content: str) -> List[Dict]:
        """Извлекает риски для расчетов"""
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
                if len(parts) >= 5 and 'риск' in parts[1].lower():
                    risks.append({
                        "risk_index": float(parts[4]) if self._is_float(parts[4]) else 0.0,
                        "priority": parts[5] if len(parts) > 5 else "medium"
                    })
        
        return risks
    
    def _calculate_content_health_index(self, themes: List, emotions: Dict, personas: List, risks: List) -> float:
        """
        Расчет Индекса Здоровья Контента (ИЗК)
        """
        # Топ-3 темы по Topic_Score
        top_themes = sorted(themes, key=lambda x: x.get('topic_score', 0), reverse=True)[:3]
        avg_topic_score = sum(t.get('topic_score', 0) for t in top_themes) / len(top_themes) if top_themes else 0
        
        # Доля позитивных эмоций
        positive_ratio = emotions.get('positive_ratio', 0.3)
        
        # Топ-3 персоны по ИВС
        top_personas = sorted(personas, key=lambda x: x.get('influence_index', 0), reverse=True)[:3]
        sum_influence = sum(p.get('influence_index', 0) for p in top_personas)
        
        # Топ-3 риска по ИУВ
        top_risks = sorted(risks, key=lambda x: x.get('risk_index', 0), reverse=True)[:3]
        avg_risk_index = sum(r.get('risk_index', 0) for r in top_risks) / len(top_risks) if top_risks else 0
        
        # Расчет итогового индекса
        health_index = (avg_topic_score * 0.3) + (positive_ratio * 100 * 0.3) + (sum_influence * 100 * 0.2) + ((1 - avg_risk_index) * 100 * 0.2)
        
        return min(health_index, 100)
    
    def _calculate_audience_evolution_vector(self, personas: List, themes: List) -> str:
        """
        Определение Вектора Развития Аудитории
        """
        if not personas:
            return "не определен"
        
        persona_types = {}
        for persona in personas:
            p_type = persona.get('type', 'unknown')
            persona_types[p_type] = persona_types.get(p_type, 0) + 1
        
        dominant_persona = max(persona_types.items(), key=lambda x: x[1])[0] if persona_types else "неизвестно"
        
        if any('эксперт' in str(p.get('type', '')).lower() for p in personas):
            target_persona = "эксперты-аналитики"
        elif any('практик' in str(p.get('type', '')).lower() for p in personas):
            target_persona = "практики-знатоки"
        else:
            target_persona = "энтузиасты-новички"
        
        return f"{dominant_persona} → {target_persona}"
    
    def _calculate_overall_priority(self, risks: List) -> str:
        """Определение общего приоритета"""
        if not risks:
            return "СРЕДНИЙ"
        
        critical_risks = [r for r in risks if r.get('priority') in ['critical', 'критический', 'high', 'высокий']]
        
        if len(critical_risks) >= 2:
            return "ВЫСОКИЙ"
        elif len(critical_risks) >= 1:
            return "СРЕДНИЙ"
        else:
            return "НИЗКИЙ"
    
    def _calculate_quality_score(self, themes: List, emotions: Dict, personas: List) -> float:
        """Расчет качества контента"""
        theme_score = min(len(themes) * 10, 40)
        emotion_score = emotions.get('positive_ratio', 0.5) * 30
        persona_score = min(len(personas) * 6, 30)
        
        return theme_score + emotion_score + persona_score
    
    def _is_float(self, value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False
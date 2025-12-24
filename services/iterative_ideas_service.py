# services/iterative_ideas_service.py
import asyncio
import re
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from database.crud import get_user_analysis_history, get_prompts
from services.ai_service import analyze_comments_with_prompt


@dataclass
class IdeaEvaluation:
    idea: str
    scores: Dict[str, float]
    feedback: str
    ai_type: str


@dataclass
class OptimizedIdea:
    original_idea: str
    optimized_idea: str
    iteration: int
    final_score: float
    confidence: float
    evaluation_history: List[IdeaEvaluation]


class AdvancedIterativeIdeasOptimizer:
    def __init__(self):
        self.criteria = {
            "engagement": {"weight": 0.25},
            "viral_potential": {"weight": 0.20},
            "uniqueness": {"weight": 0.15},
            "production_cost": {"weight": 0.15, "invert": True},
            "audience_fit": {"weight": 0.15},
            "trend_relevance": {"weight": 0.10},
        }

        self.ai_weights = {
            "creative_ai": 0.35,
            "analytical_ai": 0.35,
            "practical_ai": 0.30,
        }

    # ---------- PARSING ----------
    def parse_scores(self, text: str) -> Dict[str, float]:
        scores = {}
        text = text.lower()

        for key in self.criteria:
            match = re.search(rf"{key}.*?(\d{{1,2}})", text)
            if match:
                score = float(match.group(1))
                scores[key] = min(10, max(1, score))

        if not scores:
            for key in self.criteria:
                scores[key] = 6.0

        return scores

    # ---------- CONFIDENCE ----------
    def calculate_confidence(self, evaluations: List[IdeaEvaluation]) -> float:
        agreement = np.std(
            [np.mean(list(e.scores.values())) for e in evaluations]
        )
        confidence = max(0.4, 1 - agreement / 5)
        return round(confidence, 2)

    # ---------- FINAL SCORE ----------
    def calculate_final_score(self, evaluations: List[IdeaEvaluation]) -> float:
        total = 0
        weight_sum = 0

        for ev in evaluations:
            ai_weight = self.ai_weights[ev.ai_type]
            for k, cfg in self.criteria.items():
                score = ev.scores.get(k, 5)
                if cfg.get("invert"):
                    score = 11 - score
                total += score * cfg["weight"] * ai_weight
                weight_sum += cfg["weight"] * ai_weight

        return round(total / weight_sum, 2)

    async def evaluate(self, idea: str, prompt: str, ai_type: str) -> IdeaEvaluation:
        text = await analyze_comments_with_prompt(idea, prompt)
        scores = self.parse_scores(text)
        return IdeaEvaluation(idea, scores, text, ai_type)

    async def optimize_iteration(self, idea: str, iteration: int, prompts: Dict):
        tasks = [
            self.evaluate(idea, prompts["evaluator_creative"], "creative_ai"),
            self.evaluate(idea, prompts["evaluator_analytical"], "analytical_ai"),
            self.evaluate(idea, prompts["evaluator_practical"], "practical_ai"),
        ]

        evaluations = await asyncio.gather(*tasks)

        score = self.calculate_final_score(evaluations)
        confidence = self.calculate_confidence(evaluations)

        improve_prompt = prompts["improver"].format(
            idea=idea,
            feedback="\n".join(e.feedback for e in evaluations),
            iteration=iteration,
            current_score=score,
        )

        optimized = await analyze_comments_with_prompt(idea, improve_prompt)

        return OptimizedIdea(
            original_idea=idea,
            optimized_idea=optimized,
            iteration=iteration,
            final_score=score,
            confidence=confidence,
            evaluation_history=evaluations,
        )

    # ---------- PIPELINE ----------
    async def run(self, user_id: int) -> List[OptimizedIdea]:
        history = await get_user_analysis_history(user_id)
        if len(history) < 5:
            raise ValueError("NOT_ENOUGH_DATA")

        prompts = await get_prompts("iterative_ideas")

        ideas_text = await analyze_comments_with_prompt(
            "\n".join(history), prompts["generator"]
        )

        ideas = ideas_text.split("\n")[:10]
        results = []

        for idea in ideas:
            current = idea
            best = None

            for i in range(1, 4):
                res = await self.optimize_iteration(current, i, prompts)
                current = res.optimized_idea
                best = res

            results.append(best)

        return sorted(results, key=lambda x: x.final_score, reverse=True)


optimizer = AdvancedIterativeIdeasOptimizer()

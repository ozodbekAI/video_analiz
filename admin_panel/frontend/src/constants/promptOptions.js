// src/constants/promptOptions.js

// Categories MUST match backend categories and bot categories.
export const CATEGORIES = [
  { value: "my", label: "📹 Моё видео" },
  { value: "competitor", label: "🎯 Конкурент" },
  { value: "shorts", label: "⚡ Shorts" },
  { value: "evolution", label: "📊 Эволюция" },
];

// ✅ NEW: Interactive / Strategic Hub categories (bot callback_data bilan 1:1)
export const INTERACTIVE_CATEGORIES = [
  { value: "audience_map", label: "🗺️ Карта аудитории" },
  { value: "content_prediction", label: "🔮 Предсказание контента" },
  { value: "channel_diagnostics", label: "📊 Диагностика канала" },
  { value: "content_ideas", label: "💡 Генератор идей" },
  { value: "viral_potential", label: "⚡ Виральный потенциал" },
  { value: "iterative_ideas", label: "🧠 Итеративный генератор" },
];

export function isInteractiveCategory(category) {
  return INTERACTIVE_CATEGORIES.some((c) => c.value === category);
}

// For MY / COMPETITOR
export const BASE_ANALYSIS_TYPES = [
  { value: "simple", label: "⛏️ Simple" },
  { value: "advanced", label: "⚙️ Advanced (module-based)" },
  { value: "synthesis", label: "🔄 Synthesis" },
];

// For EVOLUTION
export const EVOLUTION_ANALYSIS_TYPES = [
  { value: "evolution_step1", label: "📝 Evolution Step 1 (Объединение)" },
  { value: "evolution_step2", label: "🔄 Evolution Step 2 (Синтез)" },
];

// Advanced module list (Admin UI dropdown).
export const ADVANCED_MODULES = [
  { value: "501", label: "501 — Базовый анализ" },
  { value: "502", label: "502 — Стратегическая оптимизация" },
  { value: "503", label: "503 — Анализ хуков" },
  { value: "504", label: "504 — Виральный потенциал" },
  { value: "505", label: "505 — Контент-план" },
];

// Shorts (category = "shorts") analysis_type is encoded as: shorts_{scale}_{level}
export const SHORTS_SCALES = [
  { value: "small", label: "🟢 Малый (<300)" },
  { value: "medium", label: "🟡 Средний (300–1000)" },
  { value: "large", label: "🔴 Большой (1000+)" },
];

export const SHORTS_LEVELS = [
  { value: "501", label: "501 — Базовый анализ" },
  { value: "502", label: "502 — Стратегическая оптимизация" },
  { value: "503", label: "503 — Анализ хуков" },
  { value: "504", label: "504 — Виральный потенциал" },
  { value: "505", label: "505 — Контент-план" },
];

export function buildShortsAnalysisType(scale, level) {
  const s = scale || "small";
  const l = level || "501";
  return `shorts_${s}_${l}`;
}

export function parseShortsAnalysisType(analysis_type) {
  if (!analysis_type) return null;
  const m = String(analysis_type).match(/^shorts_(small|medium|large)_(\d{3})$/);
  if (!m) return null;
  return { scale: m[1], level: m[2] };
}

export function defaultAnalysisTypeForCategory(category) {
  // ✅ Interactive: doim bitta prompt (type = "main")
  if (isInteractiveCategory(category)) return "main";
  if (category === "shorts") return buildShortsAnalysisType("small", "501");
  if (category === "evolution") return "evolution_step1";
  return "simple";
}

export function analysisTypeOptionsForCategory(category) {
  if (category === "evolution") return EVOLUTION_ANALYSIS_TYPES;
  if (category === "my" || category === "competitor") return BASE_ANALYSIS_TYPES;
  // shorts va interactive uchun UI alohida boshqaradi
  return [];
}

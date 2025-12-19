// src/components/PromptForm.jsx
import {
  CATEGORIES,
  INTERACTIVE_CATEGORIES,
  ADVANCED_MODULES,
  SHORTS_SCALES,
  SHORTS_LEVELS,
  buildShortsAnalysisType,
  parseShortsAnalysisType,
  defaultAnalysisTypeForCategory,
  analysisTypeOptionsForCategory,
  isInteractiveCategory,
} from "../constants/promptOptions";

const inputCls =
  "w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent";

export default function PromptForm({ data, onChange }) {
  const category = data.category || "my";
  const isShorts = category === "shorts";
  const isInteractive = isInteractiveCategory(category);

  const shortsParsed =
    parseShortsAnalysisType(data.analysis_type) || {
      scale: data.shorts_scale || "small",
      level: data.shorts_level || "501",
    };

  const analysisTypeOptions = analysisTypeOptionsForCategory(category);

  function setCategory(nextCategory) {
    const nextAnalysisType = defaultAnalysisTypeForCategory(nextCategory);

    onChange("category", nextCategory);
    onChange("analysis_type", nextAnalysisType);

    // Reset dependent fields
    onChange("module_id", null);

    // Shorts helper fields
    if (nextCategory === "shorts") {
      onChange("shorts_scale", "small");
      onChange("shorts_level", "501");
      onChange("analysis_type", buildShortsAnalysisType("small", "501"));
    } else {
      onChange("shorts_scale", "");
      onChange("shorts_level", "");
    }
  }

  function setShortsScale(scale) {
    const next = buildShortsAnalysisType(scale, shortsParsed.level);
    onChange("shorts_scale", scale);
    onChange("analysis_type", next);
  }

  function setShortsLevel(level) {
    const next = buildShortsAnalysisType(shortsParsed.scale, level);
    onChange("shorts_level", level);
    onChange("analysis_type", next);
  }

  function setAnalysisType(v) {
    onChange("analysis_type", v);
    if (v !== "advanced") onChange("module_id", null);
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Название <span className="text-red-500">*</span>
          </label>
          <input
            className={inputCls}
            placeholder="Название промпта"
            value={data.name || ""}
            onChange={(e) => onChange("name", e.target.value)}
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Категория</label>
          <select
            className={inputCls}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <optgroup label="Основные">
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </optgroup>

            <optgroup label="Interactive / Strategic Hub">
              {INTERACTIVE_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </optgroup>
          </select>
        </div>

        {/* Analysis Type (NOT shorts, NOT interactive) */}
        {!isShorts && !isInteractive && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Тип анализа</label>
            <select
              className={inputCls}
              value={data.analysis_type || defaultAnalysisTypeForCategory(category)}
              onChange={(e) => setAnalysisType(e.target.value)}
            >
              {analysisTypeOptions.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Shorts selectors */}
        {isShorts && !isInteractive && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Масштаб Shorts</label>
              <select
                className={inputCls}
                value={shortsParsed.scale}
                onChange={(e) => setShortsScale(e.target.value)}
              >
                {SHORTS_SCALES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Уровень</label>
              <select
                className={inputCls}
                value={shortsParsed.level}
                onChange={(e) => setShortsLevel(e.target.value)}
              >
                {SHORTS_LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2 text-xs text-gray-500">
              analysis_type: <span className="font-mono">{data.analysis_type || ""}</span>
            </div>
          </>
        )}

        {/* Module for advanced (NOT interactive) */}
        {!isInteractive && data.analysis_type === "advanced" && (
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Модуль (только Advanced)
            </label>
            <select
              className={inputCls}
              value={data.module_id || ""}
              onChange={(e) => onChange("module_id", e.target.value || null)}
            >
              <option value="">Выберите модуль</option>
              {ADVANCED_MODULES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Interactive info */}
        {isInteractive && (
          <div className="md:col-span-2">
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-sm text-indigo-700">
              Interactive режим: для этой категории используется <b>только один промпт</b>.
              Тип анализа фиксирован: <span className="font-mono">main</span>.
            </div>
          </div>
        )}
      </div>

      {/* Prompt Text */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Текст промпта <span className="text-red-500">*</span>
        </label>
        <textarea
          rows={14}
          className={`${inputCls} font-mono text-sm`}
          placeholder="Введите текст промпта или загрузите .txt файл"
          value={data.prompt_text || ""}
          onChange={(e) => onChange("prompt_text", e.target.value)}
        />
        <div className="mt-2 text-xs text-gray-500">
          Символов: {(data.prompt_text || "").length}
        </div>
      </div>
    </div>
  );
}

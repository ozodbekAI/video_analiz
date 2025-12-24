// src/pages/AddPrompt.jsx
import { useEffect, useState } from "react";
import AdminAPI from "../api/api";
import PromptForm from "../components/PromptForm";
import {
  buildShortsAnalysisType,
  defaultAnalysisTypeForCategory,
} from "../constants/promptOptions";

// ✅ strategic
const TWO_STEP_CATEGORIES = new Set([
  "audience_map",
  "content_prediction",
  "channel_diagnostics",
  "content_ideas",
  "viral_potential",
  // "evolution",
]);

function getDefaultAnalysisType(category) {
  if (category === "iterative_ideas") return "evaluator_creative";
  if (TWO_STEP_CATEGORIES.has(category)) return "step1";
  return defaultAnalysisTypeForCategory(category);
}

export default function AddPrompt() {
  const [data, setData] = useState({
    name: "",
    category: "my",
    analysis_type: "simple",
    module_id: null,
    prompt_text: "",
    shorts_scale: "small",
    shorts_level: "501",
  });

  function update(field, value) {
    setData((prev) => ({ ...prev, [field]: value }));
  }

  useEffect(() => {
    const isShorts = data.category === "shorts";

    if (isShorts) {
      const next = buildShortsAnalysisType(data.shorts_scale || "small", data.shorts_level || "501");
      if (data.analysis_type !== next) update("analysis_type", next);
      return;
    }

    // strategic defaults
    const next = getDefaultAnalysisType(data.category);
    if (!data.analysis_type) update("analysis_type", next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.category]);

  useEffect(() => {
    if (data.category !== "shorts") return;
    const next = buildShortsAnalysisType(data.shorts_scale || "small", data.shorts_level || "501");
    if (data.analysis_type !== next) update("analysis_type", next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.category, data.shorts_scale, data.shorts_level]);

  async function save() {
    const payload = {
      name: data.name,
      category: data.category,
      analysis_type: data.analysis_type || getDefaultAnalysisType(data.category),
      module_id: data.analysis_type === "advanced" ? (data.module_id || null) : null,
      prompt_text: data.prompt_text,
    };

    if (payload.category === "shorts" && !payload.analysis_type) {
      payload.analysis_type = buildShortsAnalysisType("small", "501");
    }

    await AdminAPI.createPrompt(payload);
    alert("Промпт добавлен");

    setData((prev) => ({
      ...prev,
      name: "",
      prompt_text: "",
    }));
  }

  return (
    <div className="p-8 max-w-4xl">
      <h2 className="text-2xl font-bold mb-6">Добавить промпт</h2>

      <PromptForm data={data} onChange={update} />

      <button onClick={save} className="btn-primary mt-6">
        Сохранить
      </button>
    </div>
  );
}

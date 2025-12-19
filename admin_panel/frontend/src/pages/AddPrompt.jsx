// src/pages/AddPrompt.jsx
import { useState } from "react";
import AdminAPI from "../api/api";
import PromptForm from "../components/PromptForm";
import { buildShortsAnalysisType } from "../constants/promptOptions";

export default function AddPrompt() {
  const [data, setData] = useState({
    name: "",
    category: "my",
    analysis_type: "simple",
    module_id: null,
    prompt_text: "",
    shorts_scale: "",
    shorts_level: "",
  });

  function update(field, value) {
    setData((prev) => ({ ...prev, [field]: value }));
  }

  async function save() {
    const payload = {
      name: data.name,
      category: data.category,
      analysis_type: data.analysis_type,
      module_id: data.analysis_type === "advanced" ? (data.module_id || null) : null,
      prompt_text: data.prompt_text,
    };

    // Shorts default fallback
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

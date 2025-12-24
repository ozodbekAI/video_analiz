// src/pages/AddPromptPage.jsx
import { useState } from "react";
import AdminAPI from "../api/api";
import PromptForm from "../components/PromptForm";
import { defaultAnalysisTypeForCategory, isInteractiveCategory } from "../constants/promptOptions";

export default function AddPromptPage() {
  const [data, setData] = useState({
    name: "",
    category: "my",
    analysis_type: defaultAnalysisTypeForCategory("my"),
    module_id: null,
    prompt_text: "",
    shorts_scale: "small",
    shorts_level: "501",
  });

  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setData((prev) => ({ ...prev, [field]: value }));
  }

  async function save() {
    if (!data.name?.trim() || !data.prompt_text?.trim()) {
      alert("Заполните обязательные поля");
      return;
    }

    setSaving(true);
    try {
      const interactive = isInteractiveCategory(data.category);

      const payload = {
        name: data.name.trim(),
        category: data.category,
        analysis_type: data.analysis_type || defaultAnalysisTypeForCategory(data.category),
        module_id:
          !interactive && data.analysis_type === "advanced"
            ? (data.module_id || null)
            : null,
        prompt_text: data.prompt_text,
      };

      await AdminAPI.createPrompt(payload);
      alert("Промпт успешно добавлен");

      setData((prev) => ({
        ...prev,
        name: "",
        prompt_text: "",
      }));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">➕ Добавить промпт</h2>

      <PromptForm data={data} onChange={update} />

      <button
        onClick={save}
        disabled={saving}
        className="mt-6 bg-green-600 text-white px-6 py-3 rounded-xl hover:bg-green-700 disabled:opacity-50"
      >
        {saving ? "Сохранение..." : "💾 Сохранить"}
      </button>
    </div>
  );
}

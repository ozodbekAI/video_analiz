// src/components/PromptModal.jsx
import { useEffect, useMemo, useState } from "react";
import { X, Upload } from "lucide-react";
import AdminAPI from "../api/api";
import PromptForm from "./PromptForm";
import {
  defaultAnalysisTypeForCategory,
  isInteractiveCategory,
} from "../constants/promptOptions";

export default function PromptModal({
  prompt,
  onClose,
  onSave,
  initialCategory,
  initialAnalysisType,
}) {
  const initial = useMemo(() => {
    const category = prompt?.category || initialCategory || "my";
    const analysis_type =
      prompt?.analysis_type ||
      initialAnalysisType ||
      defaultAnalysisTypeForCategory(category);

    return {
      name: prompt?.name || "",
      category,
      analysis_type,
      module_id: prompt?.module_id || null,
      prompt_text: prompt?.prompt_text || "",
      shorts_scale: "",
      shorts_level: "",
    };
  }, [prompt, initialCategory, initialAnalysisType]);

  const [formData, setFormData] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setFormData(initial);
    setError("");
  }, [initial]);

  function onChange(field, value) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit() {
    if (!formData.name?.trim() || !formData.prompt_text?.trim()) {
      setError("Заполните обязательные поля");
      return;
    }

    setLoading(true);
    setError("");

    const interactive = isInteractiveCategory(formData.category);

    const payload = {
      name: formData.name.trim(),
      category: formData.category,
      // ✅ Interactive: fixed analysis_type
      analysis_type: interactive ? "main" : formData.analysis_type,
      // ✅ Interactive: no module_id
      module_id: interactive
        ? null
        : formData.analysis_type === "advanced"
        ? formData.module_id || null
        : null,
      prompt_text: formData.prompt_text,
    };

    try {
      if (prompt?.id) await AdminAPI.updatePrompt(prompt.id, payload);
      else await AdminAPI.createPrompt(payload);

      await onSave?.();
      onClose?.();
    } catch (e) {
      setError(String(e?.message || "Ошибка сохранения"));
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "text/plain") {
      setError("Только .txt файлы");
      return;
    }

    try {
      const text = await file.text();
      setFormData((prev) => ({ ...prev, prompt_text: text }));
      setError("");
    } catch {
      setError("Ошибка чтения файла");
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <h3 className="text-xl font-bold text-gray-800">
              {prompt ? "✏️ Редактировать промпт" : "➕ Новый промпт"}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Категория и тип анализа должны совпадать с ботом.
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 transition">
            <X className="w-6 h-6" />
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Body */}
        <div className="p-6">
          <div className="flex items-center justify-end">
            <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 cursor-pointer text-sm">
              <Upload className="w-4 h-4" />
              Загрузить .txt
              <input type="file" accept=".txt" onChange={handleFileUpload} className="hidden" />
            </label>
          </div>

          <div className="mt-4">
            <PromptForm data={formData} onChange={onChange} />
          </div>

          <div className="mt-3 text-xs text-gray-500">
            Символов:{" "}
            <span className="font-semibold text-gray-700">{formData.prompt_text?.length || 0}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 flex gap-3 justify-end sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 rounded-xl hover:bg-gray-50 transition"
          >
            Отмена
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl hover:shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Сохранение…" : "💾 Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}

// src/pages/PromptsPage.jsx
import { useEffect, useMemo, useState } from "react";
import { Plus, Edit2, Trash2, Search } from "lucide-react";
import AdminAPI from "../api/api";
import PromptModal from "../components/PromptModal";
import {
  CATEGORIES,
  INTERACTIVE_CATEGORIES,
  SHORTS_SCALES,
  SHORTS_LEVELS,
  buildShortsAnalysisType,
  defaultAnalysisTypeForCategory,
  analysisTypeOptionsForCategory,
  isInteractiveCategory,
} from "../constants/promptOptions";

const chipActive = "bg-indigo-500 text-white shadow-lg";
const chip = "bg-gray-100 text-gray-700 hover:bg-gray-200";

const PromptsPage = () => {
  const [prompts, setPrompts] = useState([]);
  const [category, setCategory] = useState("my");
  const [analysisType, setAnalysisType] = useState("simple");
  const [shortsScale, setShortsScale] = useState("small");
  const [shortsLevel, setShortsLevel] = useState("501");
  const [searchTerm, setSearchTerm] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const isShorts = category === "shorts";
  const isInteractive = isInteractiveCategory(category);

  // Keep analysisType consistent with category
  useEffect(() => {
    if (isShorts) {
      setAnalysisType(buildShortsAnalysisType(shortsScale, shortsLevel));
      return;
    }

    setAnalysisType((prev) => {
      const opts = analysisTypeOptionsForCategory(category);
      const exists = opts.some((o) => o.value === prev);
      return exists ? prev : defaultAnalysisTypeForCategory(category);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  useEffect(() => {
    if (!isShorts) return;
    setAnalysisType(buildShortsAnalysisType(shortsScale, shortsLevel));
  }, [isShorts, shortsScale, shortsLevel]);

  useEffect(() => {
    loadPrompts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, analysisType]);

  const loadPrompts = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await AdminAPI.getPrompts({
        category,
        analysis_type: analysisType,
      });
      setPrompts(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e?.message || "Failed to load prompts");
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Удалить промпт?")) return;
    try {
      await AdminAPI.deletePrompt(id);
      loadPrompts();
    } catch (e) {
      alert(e?.message || "Ошибка удаления");
    }
  };

  const visiblePrompts = useMemo(() => {
    const s = searchTerm.trim().toLowerCase();
    if (!s) return prompts;
    return prompts.filter((p) => (p.name || "").toLowerCase().includes(s));
  }, [prompts, searchTerm]);

  const analysisOptions = useMemo(() => {
    return analysisTypeOptionsForCategory(category);
  }, [category]);

  function openAdd() {
    setShowAddModal(true);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Промпты</h1>
          <p className="text-gray-600 mt-1">
            Управление AI промптами (совместимо с ботом)
          </p>
        </div>

        <button
          onClick={openAdd}
          className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-6 py-3 rounded-xl flex items-center gap-2 hover:shadow-lg transition"
        >
          <Plus className="w-5 h-5" />
          Добавить промпт
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="flex flex-col gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Поиск промптов..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Category chips (base) */}
          <div className="flex gap-2 flex-wrap">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setCategory(c.value)}
                className={`px-4 py-2 rounded-xl font-medium transition ${
                  category === c.value ? chipActive : chip
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* Interactive chips */}
          <div className="flex gap-2 flex-wrap">
            {INTERACTIVE_CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setCategory(c.value)}
                className={`px-4 py-2 rounded-xl font-medium transition ${
                  category === c.value ? chipActive : chip
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* Analysis type selector */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {!isShorts ? (
              <div className={isInteractive ? "md:col-span-2" : ""}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {isInteractive ? "Шаг / роль промпта" : "Тип анализа"}
                </label>

                <select
                  value={analysisType}
                  onChange={(e) => setAnalysisType(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  {analysisOptions.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>

                {isInteractive && (
                  <div className="mt-2 text-xs text-gray-500">
                    В БД/боте: <span className="font-mono">{category}</span> +{" "}
                    <span className="font-mono">{analysisType}</span>
                  </div>
                )}
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Масштаб Shorts
                  </label>
                  <select
                    value={shortsScale}
                    onChange={(e) => setShortsScale(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {SHORTS_SCALES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Уровень
                  </label>
                  <select
                    value={shortsLevel}
                    onChange={(e) => setShortsLevel(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    {SHORTS_LEVELS.map((l) => (
                      <option key={l.value} value={l.value}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2 text-xs text-gray-500">
                  analysis_type (как в БД/боте):{" "}
                  <span className="font-mono">{analysisType}</span>
                </div>
              </>
            )}
          </div>

          {/* Error + Stats */}
          <div className="pt-4 border-t border-gray-200 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            {error ? (
              <div className="text-sm text-red-600">{error}</div>
            ) : (
              <div className="text-sm text-gray-600">
                Всего:{" "}
                <span className="font-semibold text-gray-800">
                  {prompts.length}
                </span>{" "}
                · Найдено:{" "}
                <span className="font-semibold text-gray-800">
                  {visiblePrompts.length}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Prompts List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : visiblePrompts.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
          <div className="text-6xl mb-4">📝</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Промпты не найдены
          </h3>
          <p className="text-gray-600">
            {searchTerm
              ? "Попробуйте изменить поисковый запрос"
              : "Добавьте первый промпт для выбранных фильтров"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {visiblePrompts.map((p) => (
            <div
              key={p.id}
              className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 truncate">
                    {p.name}
                  </h3>

                  <div className="flex gap-2 flex-wrap">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium">
                      {p.analysis_type}
                    </span>

                    {p.module_id ? (
                      <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium">
                        Module: {p.module_id}
                      </span>
                    ) : null}

                    <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-lg text-sm">
                      {(p.prompt_text?.length || 0).toLocaleString()} символов
                    </span>
                  </div>

                  <div className="mt-3 p-3 bg-gray-50 rounded-xl text-sm text-gray-700 font-mono line-clamp-2">
                    {(p.prompt_text || "").slice(0, 200)}
                    {(p.prompt_text || "").length > 200 ? "…" : ""}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingPrompt(p)}
                    className="p-2 bg-blue-100 text-blue-700 rounded-xl hover:bg-blue-200 transition"
                    title="Редактировать"
                  >
                    <Edit2 className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() => handleDelete(p.id)}
                    className="p-2 bg-red-100 text-red-700 rounded-xl hover:bg-red-200 transition"
                    title="Удалить"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showAddModal && (
        <PromptModal
          initialCategory={category}
          initialAnalysisType={analysisType}
          onClose={() => setShowAddModal(false)}
          onSave={loadPrompts}
        />
      )}

      {editingPrompt && (
        <PromptModal
          prompt={editingPrompt}
          onClose={() => setEditingPrompt(null)}
          onSave={loadPrompts}
        />
      )}
    </div>
  );
};

export default PromptsPage;

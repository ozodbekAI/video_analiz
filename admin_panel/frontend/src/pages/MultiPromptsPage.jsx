import { useEffect, useMemo, useState } from "react";
import { Plus, Edit2, Trash2, CheckCircle2 } from "lucide-react";
import AdminAPI from "../api/api";

const MultiPromptsPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("...");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: "",
    version: "1.0",
    description: "",
    prompt_text: "",
    make_active: false,
  });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await AdminAPI.getMultiPrompts();
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e?.message || "Failed to load multi-analysis prompts");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeId = useMemo(() => {
    const a = items.find((x) => x.is_active);
    return a ? a.id : null;
  }, [items]);

  function openCreate() {
    setEditing(null);
    setForm({
      name: "",
      version: "1.0",
      description: "",
      prompt_text: "",
      make_active: true,
    });
    setShowModal(true);
  }

  function openEdit(item) {
    setEditing(item);
    setForm({
      name: item.name || "",
      version: item.version || "1.0",
      description: item.description || "",
      prompt_text: item.prompt_text || "",
      make_active: false,
    });
    setShowModal(true);
  }

  async function onSave() {
    try {
      if (!form.name.trim() || !form.prompt_text.trim()) {
        alert("Name and prompt text are required");
        return;
      }

      if (editing) {
        await AdminAPI.updateMultiPrompt(editing.id, {
          name: form.name,
          version: form.version,
          description: form.description || null,
          prompt_text: form.prompt_text,
        });
      } else {
        await AdminAPI.createMultiPrompt({
          name: form.name,
          version: form.version,
          description: form.description || null,
          prompt_text: form.prompt_text,
          make_active: !!form.make_active,
        });
      }

      setShowModal(false);
      await load();
    } catch (e) {
      alert(e?.message || "Save failed");
    }
  }

  async function onActivate(id) {
    try {
      await AdminAPI.activateMultiPrompt(id);
      await load();
    } catch (e) {
      alert(e?.message || "Activate failed");
    }
  }

  async function onDelete(id) {
    if (!confirm("Удалить промпт оценщика?")) return;
    try {
      await AdminAPI.deleteMultiPrompt(id);
      await load();
    } catch (e) {
      alert(e?.message || "Delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Evaluator Prompts (ADV)</h1>
          <p className="text-gray-600 mt-1">
            Промпт оценщика для сравнения 3+ Advanced анализов (TZ-2). Активен только один.
          </p>
        </div>

        <button
          onClick={openCreate}
          className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-6 py-3 rounded-xl flex items-center gap-2 hover:shadow-lg transition"
        >
          <Plus className="w-5 h-5" />
          Добавить
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-6">
        {error ? <div className="text-sm text-red-600 mb-4">{error}</div> : null}

        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b">
                  <th className="py-3 pr-4">ID</th>
                  <th className="py-3 pr-4">Название</th>
                  <th className="py-3 pr-4">Версия</th>
                  <th className="py-3 pr-4">Активен</th>
                  <th className="py-3 pr-4">Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-b last:border-b-0">
                    <td className="py-4 pr-4 font-mono text-sm text-gray-700">{it.id}</td>
                    <td className="py-4 pr-4">
                      <div className="font-semibold text-gray-900">{it.name}</div>
                      {it.description ? (
                        <div className="text-sm text-gray-500 line-clamp-2">{it.description}</div>
                      ) : null}
                    </td>
                    <td className="py-4 pr-4 text-sm text-gray-700">{it.version}</td>
                    <td className="py-4 pr-4">
                      {it.is_active ? (
                        <div className="inline-flex items-center gap-2 text-green-700 bg-green-50 px-3 py-1 rounded-xl">
                          <CheckCircle2 className="w-4 h-4" />
                          Active
                        </div>
                      ) : (
                        <div className="text-sm text-gray-500">—</div>
                      )}
                    </td>
                    <td className="py-4 pr-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(it)}
                          className="p-2 hover:bg-gray-100 rounded-xl transition"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4 text-gray-600" />
                        </button>

                        <button
                          onClick={() => onActivate(it.id)}
                          disabled={it.id === activeId}
                          className={`px-3 py-2 rounded-xl text-sm transition ${
                            it.id === activeId
                              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                              : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                          }`}
                          title="Activate"
                        >
                          Активировать
                        </button>

                        <button
                          onClick={() => onDelete(it.id)}
                          className="p-2 hover:bg-red-50 rounded-xl transition"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {!items.length ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-500">
                      Нет промптов
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal ? (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {editing ? "Редактировать" : "Добавить"} evaluator prompt
                </h2>
                <p className="text-sm text-gray-500">Только для Advanced evaluator (TZ-2).</p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="px-3 py-2 rounded-xl hover:bg-gray-100"
              >
                Закрыть
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Название</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="v1 evaluator"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Версия</label>
                  <input
                    value={form.version}
                    onChange={(e) => setForm({ ...form, version: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="1.0"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Описание</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Кратко что поменялось"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Prompt</label>
                <textarea
                  value={form.prompt_text}
                  onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
                  rows={12}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                  placeholder="System prompt для оценщика..."
                />
              </div>

              {!editing ? (
                <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={!!form.make_active}
                    onChange={(e) => setForm({ ...form, make_active: e.target.checked })}
                  />
                  Сделать активным сразу
                </label>
              ) : null}
            </div>

            <div className="p-6 border-t flex items-center justify-end gap-2">
              <button
                onClick={() => setShowModal(false)}
                className="px-5 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 transition"
              >
                Отмена
              </button>
              <button
                onClick={onSave}
                className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:shadow-lg transition"
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default MultiPromptsPage;

import { useState } from "react";
import { api } from "../api/api";
import {
  CATEGORIES,
  LEVELS,
  ADVANCED_MODULES,
} from "../constants/promptOptions";

export default function AddPromptPage() {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("my");
  const [level, setLevel] = useState("simple");
  const [module, setModule] = useState("");
  const [text, setText] = useState("");

  async function save() {
    await api.post("/admin/prompts/", {
      name,
      category,
      analysis_level: level,
      module_id: level === "advanced" ? module : null,
      prompt_text: text,
    });

    alert("Промпт успешно добавлен");
    setName("");
    setText("");
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">➕ Добавить промпт</h2>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <input
          className="p-3 border rounded-xl"
          placeholder="Название промпта"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <select
          className="p-3 border rounded-xl"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>

        <select
          className="p-3 border rounded-xl"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          {LEVELS.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>

        {level === "advanced" && (
          <select
            className="p-3 border rounded-xl"
            value={module}
            onChange={(e) => setModule(e.target.value)}
          >
            <option value="">Выберите модуль</option>
            {ADVANCED_MODULES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        )}
      </div>

      <textarea
        rows={12}
        className="w-full p-4 border rounded-xl mb-4"
        placeholder="Текст промпта"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />

      <button
        onClick={save}
        className="bg-green-600 text-white px-6 py-3 rounded-xl hover:bg-green-700"
      >
        💾 Сохранить
      </button>
    </div>
  );
}

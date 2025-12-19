// src/pages/EditPrompt.jsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AdminAPI from "../api/api";
import PromptForm from "../components/PromptForm";

export default function EditPrompt() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    AdminAPI.getPromptById(id).then((r) => {
      setData({
        name: r.name,
        category: r.category,
        analysis_type: r.analysis_type,
        module_id: r.module_id || null,
        prompt_text: r.prompt_text,
        shorts_scale: "",
        shorts_level: "",
      });
    });
  }, [id]);

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

    await AdminAPI.updatePrompt(id, payload);
    alert("Промпт обновлён");
    nav("/prompts");
  }

  if (!data) return null;

  return (
    <div className="p-8 max-w-4xl">
      <h2 className="text-2xl font-bold mb-6">Редактирование</h2>
      <PromptForm data={data} onChange={update} />
      <button onClick={save} className="btn-primary mt-6">
        Обновить
      </button>
    </div>
  );
}

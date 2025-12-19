import { useMemo, useState } from "react";
import { X } from "lucide-react";
import AdminAPI from "../api/api";

// Botdagi logikaga yaqin qilish uchun yordamchi: video_id ni URL dan ajratib olish
function extractVideoId(url = "") {
  try {
    const u = new URL(url);
    // https://www.youtube.com/watch?v=XXXX
    const v = u.searchParams.get("v");
    if (v) return v;

    // https://youtu.be/XXXX
    if (u.hostname.includes("youtu.be")) {
      const p = u.pathname.replace("/", "");
      return p || "";
    }

    // fallback: oxirgi segment
    const parts = u.pathname.split("/").filter(Boolean);
    return parts[parts.length - 1] || "";
  } catch {
    return "";
  }
}

export default function SampleModal({ onClose, onSaved }) {
  const initial = useMemo(
    () => ({
      report_name: "",
      video_url: "",
      video_type: "regular", // regular | shorts
      // backend dict kutyapti; biz UI da JSON text orqali boshqaramiz
      analysis_data_text: JSON.stringify(
        {
          pdf_path: "",
          video_id: "",
          file_size: null,
          uploaded_at: null,
        },
        null,
        2
      ),
    }),
    []
  );

  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function setField(k, v) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  function syncVideoIdFromUrl(url) {
    const id = extractVideoId(url);
    if (!id) return;

    try {
      const obj = JSON.parse(form.analysis_data_text || "{}");
      obj.video_id = obj.video_id || id;
      setField("analysis_data_text", JSON.stringify(obj, null, 2));
    } catch {
      // agar JSON buzilgan bo‘lsa, tegmaymiz
    }
  }

  async function save() {
    setError("");

    if (!form.report_name.trim()) {
      setError("report_name majburiy");
      return;
    }
    if (!form.video_url.trim()) {
      setError("video_url majburiy");
      return;
    }
    if (!["regular", "shorts"].includes(form.video_type)) {
      setError("video_type faqat regular yoki shorts bo‘lishi kerak");
      return;
    }

    let analysis_data = {};
    try {
      analysis_data = form.analysis_data_text?.trim()
        ? JSON.parse(form.analysis_data_text)
        : {};
    } catch (e) {
      setError("analysis_data JSON noto‘g‘ri. JSON formatni tekshiring.");
      return;
    }

    const payload = {
      report_name: form.report_name.trim(),
      video_url: form.video_url.trim(),
      video_type: form.video_type,
      analysis_data,
    };

    setSaving(true);
    try {
      await AdminAPI.createSampleReport(payload);
      await onSaved?.();
      onClose?.();
    } catch (e) {
      setError(e?.message || "Saqlashda xatolik");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-800">Новый демо отчет</h3>
            <p className="text-sm text-gray-500">
              Backend: POST /admin/samples (report_name, video_url, video_type, analysis_data)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Название (report_name)
              </label>
              <input
                value={form.report_name}
                onChange={(e) => setField("report_name", e.target.value)}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
                placeholder="Например: Demo Advanced Report"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Тип видео (video_type)
              </label>
              <select
                value={form.video_type}
                onChange={(e) => setField("video_type", e.target.value)}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
              >
                <option value="regular">🎬 regular</option>
                <option value="shorts">⚡ shorts</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                YouTube URL (video_url)
              </label>
              <input
                value={form.video_url}
                onChange={(e) => {
                  const v = e.target.value;
                  setField("video_url", v);
                  syncVideoIdFromUrl(v);
                }}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
                placeholder="https://www.youtube.com/watch?v=..."
              />
              <div className="text-xs text-gray-500 mt-2">
                URL kiritilganda analysis_data ichiga video_id avtomatik qo‘yiladi (agar JSON buzilmagan bo‘lsa).
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              analysis_data (JSON)
            </label>
            <textarea
              value={form.analysis_data_text}
              onChange={(e) => setField("analysis_data_text", e.target.value)}
              rows={10}
              className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              placeholder='{"pdf_path":"...","video_id":"..."}'
            />
            <div className="text-xs text-gray-500 mt-2">
              Bu joy backendga dict sifatida ketadi. Siz botdagi kabi{" "}
              <span className="font-mono">pdf_path, video_id, file_size, uploaded_at</span>{" "}
              saqlashingiz mumkin.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t flex justify-end gap-3 bg-white">
          <button
            onClick={onClose}
            className="px-6 py-2 border rounded-xl hover:bg-gray-50"
          >
            Отмена
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-6 py-2 bg-indigo-600 text-white rounded-xl hover:shadow disabled:opacity-50"
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}

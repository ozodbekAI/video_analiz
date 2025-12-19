import { useState } from "react";
import { X, Upload } from "lucide-react";
import AdminAPI from "../api/api";

export default function SampleUploadModal({ onClose, onSaved }) {
  const [reportName, setReportName] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoType, setVideoType] = useState("regular");
  const [pdfFile, setPdfFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setError("");

    if (!reportName.trim()) return setError("Введите название отчета");
    if (!videoUrl.trim()) return setError("Введите URL видео");
    if (!pdfFile) return setError("Прикрепите PDF файл");
    if (pdfFile.type !== "application/pdf") {
      // ba'zan browser type bo'sh bo'ladi, shunda ham ruxsat berish mumkin
      // lekin odatda pdf bo'ladi
    }

    setSaving(true);
    try {
      await AdminAPI.createSampleReportWithPdf({
        report_name: reportName.trim(),
        video_url: videoUrl.trim(),
        video_type: videoType,
        pdfFile,
      });

      await onSaved?.();
      onClose?.();
    } catch (e) {
      setError(e?.message || "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden">
        <div className="p-6 border-b flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-800">Добавить демо отчет (как в боте)</h3>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-gray-100">
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="p-6 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Название отчета
              </label>
              <input
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
                placeholder="Например: Demo report #1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Тип видео
              </label>
              <select
                value={videoType}
                onChange={(e) => setVideoType(e.target.value)}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
              >
                <option value="regular">🎬 Regular</option>
                <option value="shorts">⚡ Shorts</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL видео (YouTube)
              </label>
              <input
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-indigo-500"
                placeholder="https://www.youtube.com/watch?v=..."
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-4">
            <label className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 cursor-pointer">
              <Upload className="w-4 h-4" />
              Прикрепить PDF
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              />
            </label>

            <div className="text-sm text-gray-600 truncate flex-1">
              {pdfFile ? `Файл: ${pdfFile.name}` : "PDF не выбран"}
            </div>
          </div>
        </div>

        <div className="p-6 border-t flex justify-end gap-3 bg-white">
          <button onClick={onClose} className="px-6 py-2 border rounded-xl hover:bg-gray-50">
            Отмена
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="px-6 py-2 bg-indigo-600 text-white rounded-xl hover:shadow disabled:opacity-50"
          >
            {saving ? "Загрузка..." : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}

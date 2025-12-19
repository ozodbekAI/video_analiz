import { useState, useEffect } from "react";
import { Power, Eye, Trash2, Plus, FileText } from "lucide-react";
import AdminAPI from "../api/api";
import SampleModal from "../components/SampleModal";
import SampleUploadModal from "../components/SampleUploadModal";

const SamplesPage = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [viewing, setViewing] = useState(null); // sample object
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await AdminAPI.getSampleReports();
      setReports(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load reports:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id) => {
    try {
      await AdminAPI.toggleSampleReport(id);
      loadReports();
    } catch {
      alert("Ошибка переключения статуса");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Удалить этот демо отчет?")) return;
    try {
      await AdminAPI.deleteSampleReport(id);
      loadReports();
    } catch {
      alert("Ошибка удаления");
    }
  };

  const handleView = async (id) => {
    try {
      const data = await AdminAPI.getSampleReportById(id);
      setViewing(data);
    } catch {
      alert("Ошибка загрузки отчета");
    }
  };

  const filteredReports = reports.filter((r) => {
    if (filter === "all") return true;
    if (filter === "active") return r.is_active;
    if (filter === "inactive") return !r.is_active;
    if (filter === "regular") return r.video_type === "regular";
    if (filter === "shorts") return r.video_type === "shorts";
    return true;
  });

  const stats = {
    total: reports.length,
    active: reports.filter((r) => r.is_active).length,
    regular: reports.filter((r) => r.video_type === "regular").length,
    shorts: reports.filter((r) => r.video_type === "shorts").length,
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Демо отчеты</h1>
          <p className="text-gray-500 mt-1">Управление демонстрационными отчетами</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-6 py-3 rounded-xl flex items-center gap-2 hover:shadow-lg transition"
        >
          <Plus className="w-5 h-5" />
          Добавить отчет
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl shadow-lg p-4">
          <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
          <div className="text-sm text-gray-600">Всего отчетов</div>
        </div>
        <div className="bg-white rounded-2xl shadow-lg p-4">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-sm text-gray-600">Активных</div>
        </div>
        <div className="bg-white rounded-2xl shadow-lg p-4">
          <div className="text-2xl font-bold text-blue-600">{stats.regular}</div>
          <div className="text-sm text-gray-600">Regular</div>
        </div>
        <div className="bg-white rounded-2xl shadow-lg p-4">
          <div className="text-2xl font-bold text-purple-600">{stats.shorts}</div>
          <div className="text-sm text-gray-600">Shorts</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-lg p-4 mb-6">
        <div className="flex gap-2 flex-wrap">
          {[
            { value: "all", label: "📋 Все" },
            { value: "active", label: "✅ Активные" },
            { value: "inactive", label: "❌ Неактивные" },
            { value: "regular", label: "🎬 Regular" },
            { value: "shorts", label: "⚡ Shorts" },
          ].map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-4 py-2 rounded-xl font-medium transition ${
                filter === f.value
                  ? "bg-indigo-500 text-white shadow-lg"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredReports.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
          <div className="text-6xl mb-4">📄</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Отчеты не найдены</h3>
          <p className="text-gray-500">Добавьте первый демо отчет</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <div key={report.id} className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition">
              <div className="flex items-start justify-between">
                {/* Report Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white">
                      <FileText className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">{report.report_name}</h3>
                      <p className="text-sm text-gray-500">{report.video_url}</p>
                    </div>
                  </div>

                  {/* Tags */}
                  <div className="flex gap-2 flex-wrap mt-3">
                    <span
                      className={`px-3 py-1 rounded-lg text-sm font-medium ${
                        report.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {report.is_active ? "✅ Активен" : "❌ Неактивен"}
                    </span>
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium">
                      {report.video_type === "shorts" ? "⚡ Shorts" : "🎬 Regular"}
                    </span>
                    {report.created_at && (
                      <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-lg text-sm">
                        📅 {new Date(report.created_at).toLocaleDateString("ru-RU")}
                      </span>
                    )}
                  </div>

                  {/* Analysis Data Preview */}
                  {report.analysis_data && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-xl text-xs text-gray-600">
                      <div className="font-semibold mb-1">Данные анализа:</div>
                      {report.analysis_data.pdf_path && (
                        <div>📄 PDF: {String(report.analysis_data.pdf_path).split("/").pop()}</div>
                      )}
                      {report.analysis_data.video_id && <div>🎬 Video ID: {report.analysis_data.video_id}</div>}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleToggle(report.id)}
                    className={`p-2 rounded-xl transition ${
                      report.is_active ? "bg-green-100 text-green-600 hover:bg-green-200" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                    title="Переключить статус"
                  >
                    <Power className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() => handleView(report.id)}
                    className="p-2 bg-blue-100 text-blue-600 rounded-xl hover:bg-blue-200 transition"
                    title="Просмотр"
                  >
                    <Eye className="w-5 h-5" />
                  </button>

                  <button
                    onClick={() => handleDelete(report.id)}
                    className="p-2 bg-red-100 text-red-600 rounded-xl hover:bg-red-200 transition"
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

      {/* Add Modal */}
      {showAddModal && (
        <SampleUploadModal
          onClose={() => setShowAddModal(false)}
          onSaved={loadReports}
        />
      )}

      {/* View Modal (simple) */}
      {viewing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-gray-800">{viewing.report_name}</h3>
                <p className="text-sm text-gray-500">{viewing.video_url}</p>
              </div>
              <button
                onClick={() => setViewing(null)}
                className="px-4 py-2 border rounded-xl hover:bg-gray-50"
              >
                Закрыть
              </button>
            </div>
            <div className="p-6">
              <div className="text-sm text-gray-700 mb-3">
                video_type: <span className="font-mono">{viewing.video_type}</span> | active:{" "}
                <span className="font-mono">{String(viewing.is_active)}</span>
              </div>
              <pre className="p-4 bg-gray-50 rounded-xl text-xs overflow-auto">
                {JSON.stringify(viewing.analysis_data || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SamplesPage;

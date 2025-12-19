// src/pages/Dashboard.jsx
import { useEffect, useMemo, useState } from 'react';
import { BarChart3, Users, Video, Activity } from 'lucide-react';
import AdminAPI from '../api/api';

const cardCls =
  'bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError('');
        const data = await AdminAPI.getStats();
        setStats(data);
      } catch (e) {
        setError(e?.message || 'Ошибка загрузки');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const analysisRows = useMemo(() => {
    const m = stats?.analysis_types || {};
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [stats]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Дашборд</h1>
        <p className="text-gray-500 mt-1">Сводка по системе</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <div className={cardCls}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Пользователи</p>
                  <p className="text-3xl font-bold text-gray-800">{stats?.total_users ?? 0}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Сегодня: <span className="font-semibold text-gray-700">{stats?.users_today ?? 0}</span>
                  </p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center">
                  <Users className="w-6 h-6 text-indigo-600" />
                </div>
              </div>
            </div>

            <div className={cardCls}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Видео</p>
                  <p className="text-3xl font-bold text-gray-800">{stats?.total_videos ?? 0}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Сегодня: <span className="font-semibold text-gray-700">{stats?.videos_today ?? 0}</span>
                  </p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-purple-50 flex items-center justify-center">
                  <Video className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </div>

            <div className={cardCls}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">AI запросы</p>
                  <p className="text-3xl font-bold text-gray-800">{stats?.total_ai_requests ?? stats?.total_requests ?? 0}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Сегодня: <span className="font-semibold text-gray-700">{stats?.ai_requests_today ?? stats?.requests_today ?? 0}</span>
                  </p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center">
                  <Activity className="w-6 h-6 text-emerald-600" />
                </div>
              </div>
            </div>

            <div className={cardCls}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Типы анализов</p>
                  <p className="text-3xl font-bold text-gray-800">{analysisRows.length}</p>
                  <p className="text-sm text-gray-500 mt-1">По счетчику AIResponse</p>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-gray-50 flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-gray-700" />
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h2 className="text-lg font-semibold text-gray-800">Распределение по типам анализа</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500">
                    <th className="py-2 pr-6">Тип</th>
                    <th className="py-2">Количество</th>
                  </tr>
                </thead>
                <tbody>
                  {analysisRows.map(([k, v]) => (
                    <tr key={k} className="border-t">
                      <td className="py-3 pr-6 font-mono text-gray-800">{k}</td>
                      <td className="py-3 font-semibold text-gray-800">{v}</td>
                    </tr>
                  ))}
                  {analysisRows.length === 0 && (
                    <tr>
                      <td className="py-4 text-gray-500" colSpan={2}>
                        Данных нет
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

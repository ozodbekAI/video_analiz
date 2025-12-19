// src/pages/UsersPage.jsx
import { useState, useEffect } from 'react';
import { Search, RefreshCw, Edit2, UserCheck } from 'lucide-react';
import AdminAPI from '../api/api';

const UsersPage = () => {
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await AdminAPI.getUsers();
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLimitChange = async (userId, currentLimit) => {
    const newLimit = prompt('Новый лимит анализов:', currentLimit);
    if (!newLimit || isNaN(newLimit)) return;

    try {
      await AdminAPI.updateUserLimit(userId, parseInt(newLimit));
      loadUsers();
    } catch (error) {
      alert('Ошибка обновления лимита');
    }
  };

  const handleReset = async (userId) => {
    if (!confirm('Сбросить использование для этого пользователя?')) return;

    try {
      await AdminAPI.resetUserUsage(userId);
      loadUsers();
    } catch (error) {
      alert('Ошибка сброса');
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.user_id?.toString().includes(searchTerm)
  );

  const tariffColors = {
    free: 'bg-gray-100 text-gray-700',
    starter: 'bg-blue-100 text-blue-700',
    pro: 'bg-purple-100 text-purple-700',
    business: 'bg-orange-100 text-orange-700',
    enterprise: 'bg-red-100 text-red-700',
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Пользователи</h1>
          <p className="text-gray-500 mt-1">Управление пользователями системы</p>
        </div>
        <button
          onClick={loadUsers}
          className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-6 py-3 rounded-xl flex items-center gap-2 hover:shadow-lg transition"
        >
          <RefreshCw className="w-5 h-5" />
          Обновить
        </button>
      </div>

      {/* Search */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Поиск по ID или username..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <div className="mt-4 text-sm text-gray-600">
          Найдено пользователей: <span className="font-semibold">{filteredUsers.length}</span>
        </div>
      </div>

      {/* Users List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
          <div className="text-6xl mb-4">👥</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">
            Пользователи не найдены
          </h3>
          <p className="text-gray-500">Попробуйте изменить поисковый запрос</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredUsers.map((user) => (
            <div
              key={user.user_id}
              className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition"
            >
              <div className="flex items-center justify-between">
                {/* User Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                      {user.username?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">
                        @{user.username || 'Unknown'}
                      </h3>
                      <p className="text-sm text-gray-500">ID: {user.user_id}</p>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex gap-2 flex-wrap mt-3">
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium">
                      📊 {user.analyses_used}/{user.analyses_limit}
                    </span>
                    <span
                      className={`px-3 py-1 rounded-lg text-sm font-medium ${
                        tariffColors[user.tariff_plan] || tariffColors.free
                      }`}
                    >
                      👑 {user.tariff_plan || 'free'}
                    </span>
                    {user.verification_status === 'verified' && (
                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm font-medium">
                        ✓ Verified
                      </span>
                    )}
                    {user.created_at && (
                      <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-lg text-sm">
                        📅 {new Date(user.created_at).toLocaleDateString('ru-RU')}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleLimitChange(user.user_id, user.analyses_limit)}
                    className="px-4 py-2 bg-blue-100 text-blue-600 rounded-xl hover:bg-blue-200 transition flex items-center gap-2"
                    title="Изменить лимит"
                  >
                    <Edit2 className="w-4 h-4" />
                    Лимит
                  </button>
                  <button
                    onClick={() => handleReset(user.user_id)}
                    className="px-4 py-2 bg-green-100 text-green-600 rounded-xl hover:bg-green-200 transition"
                    title="Сбросить использование"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-4">
                <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                  <span>Использовано</span>
                  <span>
                    {((user.analyses_used / user.analyses_limit) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all"
                    style={{
                      width: `${Math.min((user.analyses_used / user.analyses_limit) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UsersPage;
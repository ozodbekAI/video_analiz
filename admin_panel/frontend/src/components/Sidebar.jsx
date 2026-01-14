// src/components/Sidebar.jsx
import { Settings, BarChart3, FileText, CheckCircle2, Users, Download, Power, Menu, X } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, sidebarOpen, setSidebarOpen, onLogout }) => {
  const tabs = [
    { id: 'dashboard', label: 'Дашборд', icon: BarChart3 },
    { id: 'prompts', label: 'Промпты', icon: FileText },
    { id: 'multi_prompts', label: 'Evaluator (ADV)', icon: CheckCircle2 },
    { id: 'users', label: 'Пользователи', icon: Users },
    { id: 'samples', label: 'Демо отчеты', icon: Download },
  ];

  return (
    <div
      className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-white shadow-xl transition-all duration-300 flex flex-col`}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200 flex items-center justify-between">
        {sidebarOpen && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-800">Admin</h1>
              <p className="text-xs text-gray-500">Panel</p>
            </div>
          </div>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-gray-100 rounded-xl transition"
        >
          {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${
              activeTab === tab.id
                ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title={!sidebarOpen ? tab.label : ''}
          >
            <tab.icon className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span className="font-medium">{tab.label}</span>}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl transition"
          title={!sidebarOpen ? 'Выйти' : ''}
        >
          <Power className="w-5 h-5 flex-shrink-0" />
          {sidebarOpen && <span className="font-medium">Выйти</span>}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;

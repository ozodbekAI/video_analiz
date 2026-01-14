// src/App.jsx
import { useEffect, useState } from 'react';
import AdminAPI from './api/api';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import PromptsPage from './pages/PromptsPage';
import MultiPromptsPage from './pages/MultiPromptsPage';
import UsersPage from './pages/UsersPage';
import SamplesPage from './pages/SamplesPage';
import Sidebar from './components/Sidebar';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (token) {
      AdminAPI.setToken(token);
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = () => setIsAuthenticated(true);

  const handleLogout = () => {
    AdminAPI.clearToken();
    setIsAuthenticated(false);
    setActiveTab('dashboard');
  };

  if (!isAuthenticated) return <LoginPage onLogin={handleLogin} />;

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        onLogout={handleLogout}
      />

      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'prompts' && <PromptsPage />}
        {activeTab === 'multi_prompts' && <MultiPromptsPage />}
        {activeTab === 'users' && <UsersPage />}
        {activeTab === 'samples' && <SamplesPage />}
      </main>
    </div>
  );
};

export default App;

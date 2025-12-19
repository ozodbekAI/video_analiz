// src/api/api.js
// Admin Panel API client (FastAPI backend)

const API_BASE = import.meta?.env?.VITE_API_BASE || 'http://localhost:8000';

function buildQuery(paramsObj = {}) {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(paramsObj)) {
    if (v === undefined || v === null || v === '') continue;
    params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

class AdminAPI {
  static token = localStorage.getItem('admin_token') || '';

  static setToken(token) {
    this.token = token || '';
    if (this.token) localStorage.setItem('admin_token', this.token);
    else localStorage.removeItem('admin_token');
  }

  static clearToken() {
    this.setToken('');
  }

  static _headers(extra = {}) {
    const h = { ...extra };
    // NOTE: Do not set Content-Type for FormData uploads.
    if (!('Content-Type' in h)) h['Content-Type'] = 'application/json';
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  static async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
      ...options,
      headers: this._headers(options.headers || {}),
    });

    // Some endpoints can return empty body.
    const text = await res.text().catch(() => '');
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { _raw: text };
      }
    }

    if (!res.ok) {
      const msg =
        (data && (data.detail || data.message)) ||
        `HTTP ${res.status} ${res.statusText}`;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      err.status = res.status;
      err.payload = data;
      throw err;
    }

    return data;
  }

  // ==================== AUTH ====================
  static async login(username, password) {
    const qs = buildQuery({ username, password });
    const data = await this.request(`/admin/login${qs}`, { method: 'POST' });
    this.setToken(data?.token || '');
    return data;
  }

  // ==================== PROMPTS ====================
  // Backend: GET /admin/prompts/?category=&analysis_type=
  static async getPrompts({ category = null, analysis_type = null } = {}) {
    const qs = buildQuery({ category, analysis_type });
    return this.request(`/admin/prompts/${qs}`);
  }

  static async getPromptById(id) {
    return this.request(`/admin/prompts/${id}`);
  }

  static async createPrompt(payload) {
    return this.request('/admin/prompts/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updatePrompt(id, payload) {
    return this.request(`/admin/prompts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  static async deletePrompt(id) {
    return this.request(`/admin/prompts/${id}`, { method: 'DELETE' });
  }

  static async reorderPrompts(orders) {
    return this.request('/admin/prompts/reorder', {
      method: 'POST',
      body: JSON.stringify({ orders }),
    });
  }

  // ==================== STATS ====================
  static async getStats() {
    return this.request('/admin/stats');
  }

  static async getTopUsers(limit = 10) {
    return this.request(`/admin/stats/top-users${buildQuery({ limit })}`);
  }

  static async getRecentVideos(limit = 10) {
    return this.request(`/admin/stats/recent-videos${buildQuery({ limit })}`);
  }

  // ==================== USERS ====================
  static async getUsers({ search = '', page = 1, limit = 20 } = {}) {
    return this.request(`/admin/users${buildQuery({ search, page, limit })}`);
  }

  static async getUserById(userId) {
    return this.request(`/admin/users/${userId}`);
  }

  static async updateUserLimit(userId, limit) {
    return this.request(`/admin/users/${userId}/limit`, {
      method: 'PUT',
      body: JSON.stringify({ limit }),
    });
  }

  static async resetUserUsage(userId) {
    return this.request(`/admin/users/${userId}/reset`, { method: 'POST' });
  }

  static async updateUserTariff(userId, tariff) {
    return this.request(`/admin/users/${userId}/tariff`, {
      method: 'PUT',
      body: JSON.stringify({ tariff }),
    });
  }

  // ==================== SAMPLE REPORTS ====================
  static async getSampleReports(video_type = null) {
    const qs = buildQuery({ video_type });
    return this.request(`/admin/samples${qs}`);
  }

  static async getSampleReportById(id) {
    return this.request(`/admin/samples/${id}`);
  }

  static async createSampleReportWithPdf({ report_name, video_url, video_type, pdfFile }) {
    const form = new FormData();
    form.append("report_name", report_name);
    form.append("video_url", video_url);
    form.append("video_type", video_type || "regular");
    form.append("pdf", pdfFile);

    const res = await fetch(`${API_BASE}/admin/samples/upload`, {
      method: "POST",
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      body: form,
    });

    const text = await res.text().catch(() => "");
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch { data = { _raw: text }; }
    }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }

    return data;
  }

  static async toggleSampleReport(id) {
    return this.request(`/admin/samples/${id}/toggle`, { method: 'POST' });
  }

  static async deleteSampleReport(id) {
    return this.request(`/admin/samples/${id}`, { method: 'DELETE' });
  }


  // ==================== FILE UPLOAD ====================
  static async uploadFile(file, type = 'prompt') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    const res = await fetch(`${API_BASE}/admin/upload`, {
      method: 'POST',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      body: formData,
    });

    const text = await res.text().catch(() => '');
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { _raw: text };
      }
    }

    if (!res.ok) {
      const msg =
        (data && (data.detail || data.message)) ||
        `Upload failed: HTTP ${res.status}`;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    return data;
  }
}

export default AdminAPI;

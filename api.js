/**
 * Red Lens — API Service Module
 * Handles centralized REST communication between frontend and FastAPI backend.
 * Provides error handling, loading states, network failure recovery, and offline fallback.
 */

(function (window) {
  "use strict";

  // Determine Backend Base URL
  // If hosted on FastAPI port 8000, use relative path; otherwise default to http://localhost:8000
  const defaultBaseURL =
    window.REDLENS_API_URL ||
    (location.port === "8000" ? "" : "http://localhost:8000");

  const LS_KEY = "anemiascan.records.v2";

  class ApiService {
    constructor(baseURL) {
      this.baseURL = (baseURL || defaultBaseURL).replace(/\/+$/, "");
      this.isOnline = false;
      this.onStatusChange = null;
    }

    /**
     * Internal request wrapper with timeout and robust error parsing
     */
    async request(endpoint, options = {}) {
      const url = `${this.baseURL}${endpoint}`;
      const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
      };

      const config = {
        ...options,
        headers
      };

      // Add 25-second timeout controller
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 25000);
      config.signal = controller.signal;

      try {
        const response = await fetch(url, config);
        clearTimeout(timeoutId);

        let data = null;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          data = await response.json();
        } else {
          data = { message: await response.text() };
        }

        if (!response.ok) {
          const errorMsg =
            data.error ||
            data.detail ||
            data.message ||
            `Server error (HTTP ${response.status})`;
          const err = new Error(errorMsg);
          err.status = response.status;
          err.data = data;
          throw err;
        }

        this._setOnline(true);
        return data;
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name === "AbortError") {
          throw new Error("Request timed out. The server took too long to respond.");
        }
        if (err instanceof TypeError && err.message.includes("fetch")) {
          this._setOnline(false);
          throw new Error("Cannot reach Red Lens backend. Ensure the server is running on " + (this.baseURL || "port 8000"));
        }
        throw err;
      }
    }

    _setOnline(status) {
      if (this.isOnline !== status) {
        this.isOnline = status;
        if (typeof this.onStatusChange === "function") {
          this.onStatusChange(status);
        }
      }
    }

    /**
     * Check backend health & AI service configuration
     */
    async checkHealth() {
      try {
        const data = await this.request("/api/health", { method: "GET" });
        this._setOnline(true);
        return data;
      } catch (err) {
        this._setOnline(false);
        throw err;
      }
    }

    /**
     * Multi-modal screening analysis (eye, nail, sensor, vitals)
     */
    async analyzeScreening(screeningData) {
      return await this.request("/api/analyze", {
        method: "POST",
        body: JSON.stringify(screeningData)
      });
    }

    /**
     * Deterministic agent evaluation
     */
    async runAgent(context) {
      return await this.request("/api/agent", {
        method: "POST",
        body: JSON.stringify(context || {})
      });
    }

    /**
     * Send message to conversational AI assistant
     */
    async sendChat(message, history = [], language = "en", context = null) {
      return await this.request("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          history,
          language,
          context
        })
      });
    }

    /**
     * Submit raw/calibrated sensor reading
     */
    async submitSensor(value, source = "serial", unit = "g/dL", vitals = null) {
      return await this.request("/api/sensor/reading", {
        method: "POST",
        body: JSON.stringify({ value, source, unit, vitals })
      });
    }

    /**
     * Retrieve screening history records with search and filters.
     * Falls back to localStorage if backend is offline.
     */
    async getHistory(query = "", filterResult = "") {
      try {
        const params = new URLSearchParams();
        if (query) params.append("q", query);
        if (filterResult) params.append("filter_result", filterResult);

        const qs = params.toString() ? `?${params.toString()}` : "";
        const res = await this.request(`/api/history${qs}`, { method: "GET" });
        return res.records || [];
      } catch (err) {
        console.warn("[RedLens API] Backend offline, loading from localStorage fallback:", err.message);
        // Fallback to localStorage
        try {
          const local = JSON.parse(localStorage.getItem(LS_KEY)) || [];
          return local.filter((r) => {
            const matchesQuery =
              !query ||
              `${r.id} ${r.name} ${r.village || ""}`.toLowerCase().includes(query.toLowerCase());
            const matchesFilter =
              !filterResult || (r.combined && r.combined.startsWith(filterResult));
            return matchesQuery && matchesFilter;
          });
        } catch (e) {
          return [];
        }
      }
    }

    /**
     * Save a screening record.
     * Saves to backend SQLite DB, and mirrors to localStorage for offline resilience.
     */
    async saveRecord(record) {
      // 1. Mirror to local storage first
      try {
        const local = JSON.parse(localStorage.getItem(LS_KEY)) || [];
        const filtered = local.filter((x) => !(x.id === record.id && x.dt === record.dt));
        filtered.unshift(record);
        localStorage.setItem(LS_KEY, JSON.stringify(filtered));
      } catch (e) {
        console.warn("Local storage write failed:", e);
      }

      // 2. Persist to backend database
      try {
        const res = await this.request("/api/history", {
          method: "POST",
          body: JSON.stringify(record)
        });
        return { success: true, id: res.id, remote: true };
      } catch (err) {
        console.warn("[RedLens API] Saved locally; backend sync failed:", err.message);
        return { success: true, id: record.rid || record.id, remote: false, error: err.message };
      }
    }

    /**
     * Delete a screening record by ID.
     */
    async deleteRecord(recordId, recordDt = "") {
      // 1. Remove from local storage
      try {
        const local = JSON.parse(localStorage.getItem(LS_KEY)) || [];
        const filtered = local.filter((r) => {
          if (recordDt && r.dt === recordDt) return false;
          return r.id !== recordId && r.rid !== recordId;
        });
        localStorage.setItem(LS_KEY, JSON.stringify(filtered));
      } catch (e) {}

      // 2. Remove from backend database
      try {
        await this.request(`/api/history/${encodeURIComponent(recordId)}`, {
          method: "DELETE"
        });
        return true;
      } catch (err) {
        console.warn("[RedLens API] Remote deletion warning:", err.message);
        return false;
      }
    }
  }

  // Export singleton to global scope
  window.RedLensAPI = new ApiService();
})(window);

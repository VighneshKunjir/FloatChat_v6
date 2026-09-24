import { ForecastResult, ArgoProfile, ChatMessage } from '../types.ts';

const API_BASE = '/api';

export interface FloatSummary {
  wmo_id: string;
  name: string;
  baseLat: number;
  baseLon: number;
  cycles: number[];
  defaultCycle: number;
}

export interface ChatResponse {
  text: string;
  citations: string[];
  verified: boolean;
  forecast_context?: ForecastResult;
}

export const apiService = {
  async getHealth(): Promise<{ status: string; service: string }> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getFloats(): Promise<FloatSummary[]> {
    const res = await fetch(`${API_BASE}/floats`);
    if (!res.ok) throw new Error(`Failed to load floats: ${res.statusText}`);
    return res.json();
  },

  async getProfiles(wmoId: string): Promise<ArgoProfile[]> {
    const res = await fetch(`${API_BASE}/profiles/${wmoId}`);
    if (!res.ok) throw new Error(`Failed to load profiles for ${wmoId}: ${res.statusText}`);
    return res.json();
  },

  async runForecast(wmoId: string, cycle: number): Promise<ForecastResult> {
    const res = await fetch(`${API_BASE}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wmoId, cycle })
    });
    if (!res.ok) throw new Error(`Forecast computation failed: ${res.statusText}`);
    return res.json();
  },

  async sendChatMessage(query: string, wmoId: string, cycle: number): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, wmoId, cycle })
    });
    if (!res.ok) throw new Error(`Chat generation failed: ${res.statusText}`);
    return res.json();
  }
};

export type { ChatMessage };

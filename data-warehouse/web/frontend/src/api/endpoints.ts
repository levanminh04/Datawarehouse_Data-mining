import { apiGet, apiPost } from "./client";
import type {
  DashboardSummary,
  EtlLogsResponse,
  EtlRunResponse,
  QualityResponse,
  TableResult
} from "./types";

export const getHealth = () => apiGet<{ status: string }>("/api/health");
export const getHealthDb = () => apiGet<{ status: string; oracle_ping: number }>("/api/health/db");

export const getDashboardSummary = () => apiGet<DashboardSummary>("/api/dashboard/summary");

export const runEtl = () => apiPost<EtlRunResponse>("/api/etl/run");
export const getEtlLogs = (
  limit: number,
  opts: { status?: string; job_name?: string; from_time?: string; to_time?: string } = {}
) => {
  const usp = new URLSearchParams({ limit: String(limit) });
  if (opts.status) usp.set("status", opts.status);
  if (opts.job_name) usp.set("job_name", opts.job_name);
  if (opts.from_time) usp.set("from_time", opts.from_time);
  if (opts.to_time) usp.set("to_time", opts.to_time);
  return apiGet<EtlLogsResponse>(`/api/etl/logs?${usp.toString()}`);
};

export const getOlap = (question: number, limit?: number, params: Record<string, string> = {}) => {
  const usp = new URLSearchParams({ ...params });
  if (typeof limit === "number") {
    usp.set("limit", String(limit));
  }
  return apiGet<TableResult | Record<string, TableResult>>(`/api/olap/${question}?${usp.toString()}`);
};

export const getQualityChecks = () => apiGet<QualityResponse>("/api/quality/checks");

export const buildOlapExportUrl = (question: number, limit?: number, params: Record<string, string> = {}) => {
  const usp = new URLSearchParams({ question: String(question), ...params });
  if (typeof limit === "number") {
    usp.set("limit", String(limit));
  }
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  return `${baseUrl}/api/olap/export?${usp.toString()}`;
};

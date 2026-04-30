export type EtlJobStatus = {
  log_id: number;
  job_name: string;
  status: string;
  row_count: number;
  note: string | null;
  finished_at: string | null;
};

export type DashboardSummary = {
  table_counts: Record<string, number>;
  last_run_all: EtlJobStatus | null;
  last_load_jobs: EtlJobStatus[];
  etl_error_24h: number;
};

export type TableResult = {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  count: number;
  params?: Record<string, unknown>;
};

export type EtlRunResponse = {
  status: string;
  elapsed_seconds: number;
  last_run?: EtlJobStatus;
};

export type EtlLogsResponse = {
  count: number;
  rows: Array<Record<string, unknown>>;
};

export type QualityCheck = {
  name: string;
  dw_value: number | null;
  source_value: number | null;
  match: boolean | null;
  note: string;
  error: string | null;
};

export type QualityResponse = {
  summary: {
    total: number;
    ok: number;
    failed: number;
    unavailable: number;
  };
  checks: QualityCheck[];
};

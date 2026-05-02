import { useMemo, useState } from "react";
import { Button, Card, Input, Select, Space, Typography, message } from "antd";
import { buildOlapExportUrl, getOlap } from "../api/endpoints";
import type { TableResult } from "../api/types";
import JsonTable from "../components/JsonTable";

const { Text } = Typography;

type QueryResult = { key: string; data: TableResult };
type ParamDef = { key: string; label: string; placeholder?: string };

function isTableResult(value: TableResult | Record<string, TableResult>): value is TableResult {
  return (
    typeof value === "object" &&
    value !== null &&
    "rows" in value &&
    "columns" in value &&
    "count" in value
  );
}

const PARAM_DEFS: Record<number, ParamDef[]> = {
  1: [],
  2: [],
  3: [{ key: "ma_kh", label: "MaKH", placeholder: "vd: 10001" }],
  4: [
    { key: "ma_mh", label: "MaMH", placeholder: "vd: 3969" },
    { key: "min_so_luong_ton", label: "Min SoLuongTon", placeholder: "vd: 100" }
  ],
  5: [],
  6: [{ key: "ma_kh", label: "MaKH", placeholder: "vd: 10001" }],
  7: [
    { key: "ma_mh", label: "MaMH", placeholder: "vd: 1" },
    { key: "ma_thanh_pho", label: "MaThanhPho", placeholder: "vd: 17" }
  ],
  8: [{ key: "ma_don", label: "MaDon", placeholder: "vd: 10000" }],
  9: [{ key: "section", label: "Export section", placeholder: "du_lich|buu_dien|ca_hai|thong_ke" }]
};

export default function OlapPage() {
  const [question, setQuestion] = useState<number>(1);
  const [limitMode, setLimitMode] = useState<string>("5");
  const [params, setParams] = useState<Record<string, string>>({});
  const [viewMode, setViewMode] = useState<"detail" | "summary">("detail");
  const [sliceColumn, setSliceColumn] = useState<string>("");
  const [sliceValue, setSliceValue] = useState<string>("");
  const [groupBy, setGroupBy] = useState<string>("");
  const [sumColumn, setSumColumn] = useState<string>("");
  const [appliedSliceColumn, setAppliedSliceColumn] = useState<string>("");
  const [appliedSliceValue, setAppliedSliceValue] = useState<string>("");
  const [appliedGroupBy, setAppliedGroupBy] = useState<string>("");
  const [appliedSumColumn, setAppliedSumColumn] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QueryResult[]>([]);

  const questionOptions = useMemo(
    () => Array.from({ length: 9 }).map((_, i) => ({ label: `Cau ${i + 1}`, value: i + 1 })),
    []
  );
  const paramDefs = PARAM_DEFS[question] ?? [];
  const allColumns = results.length > 0 ? results[0].data.columns : [];

  const handleRun = async () => {
    setLoading(true);
    try {
      const limit = limitMode === "all" ? undefined : Number(limitMode);
      const queryParams = Object.fromEntries(
        Object.entries(params).filter(([_, v]) => v != null && String(v).trim() !== "" && _ !== "section")
      );
      const response = await getOlap(question, limit, queryParams);

      if (isTableResult(response)) {
        setResults([{ key: `Cau ${question}`, data: response }]);
      } else {
        const group = Object.entries(response).map(([key, value]) => ({ key, data: value }));
        setResults(group);
      }
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  const hasRun = results.length > 0;

  const handleExport = () => {
    const limit = limitMode === "all" ? undefined : Number(limitMode);
    const url = buildOlapExportUrl(question, limit, params);
    window.open(url, "_blank");
  };

  const handleApplyFilter = () => {
    setAppliedSliceColumn(sliceColumn);
    setAppliedSliceValue(sliceValue);
    setAppliedGroupBy(groupBy);
    setAppliedSumColumn(sumColumn);
  };

  const applySlice = (rows: Array<Record<string, unknown>>) => {
    if (!appliedSliceColumn || !appliedSliceValue.trim()) return rows;
    const needle = appliedSliceValue.toLowerCase();
    return rows.filter((row) => String(row[appliedSliceColumn] ?? "").toLowerCase().includes(needle));
  };

  const buildSummary = (rows: Array<Record<string, unknown>>) => {
    if (!appliedGroupBy) return rows;
    const bucket = new Map<string, { group: string; row_count: number; sum_value: number }>();
    for (const row of rows) {
      const key = String(row[appliedGroupBy] ?? "(null)");
      if (!bucket.has(key)) {
        bucket.set(key, { group: key, row_count: 0, sum_value: 0 });
      }
      const item = bucket.get(key)!;
      item.row_count += 1;
      if (appliedSumColumn) {
        const n = Number(row[appliedSumColumn] ?? 0);
        if (!Number.isNaN(n)) item.sum_value += n;
      }
    }
    return Array.from(bucket.values()).sort((a, b) => b.row_count - a.row_count);
  };

  return (
    <Card
      className="page-card"
      title="OLAP Explorer"
      extra={
        <Space>
          <Button type="primary" loading={loading} onClick={handleRun}>
            Run OLAP
          </Button>
          {hasRun && <Button onClick={handleExport}>Export CSV</Button>}
        </Space>
      }
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Space wrap style={{ paddingInlineStart: 12 }}>
          <Text>Cau:</Text>
          <Select
            style={{ width: 120 }}
            value={question}
            options={questionOptions}
            onChange={(v) => {
              setQuestion(v);
              setParams({});
              setResults([]);
              setSliceColumn("");
              setSliceValue("");
              setGroupBy("");
              setSumColumn("");
              setAppliedSliceColumn("");
              setAppliedSliceValue("");
              setAppliedGroupBy("");
              setAppliedSumColumn("");
            }}
          />
          <Text>Limit:</Text>
          <Select
            style={{ width: 140 }}
            value={limitMode}
            onChange={setLimitMode}
            options={[
              { label: "5", value: "5" },
              { label: "10", value: "10" },
              { label: "20", value: "20" },
              { label: "50", value: "50" },
              { label: "Tat ca", value: "all" }
            ]}
          />
        </Space>

        <Space wrap style={{ paddingInlineStart: 12 }}>
          {paramDefs.map((def) => (
            <Input
              key={def.key}
              style={{ width: 220 }}
              placeholder={`${def.label} (${def.placeholder ?? ""})`}
              value={params[def.key] ?? ""}
              onChange={(e) => setParams((prev) => ({ ...prev, [def.key]: e.target.value }))}
            />
          ))}
        </Space>

        {results.length === 0 && <Text type="secondary">Chua co du lieu. Chon cau va bam Run OLAP.</Text>}
        {results.map((item, idx) => (
          <Card key={item.key} size="small">
            {idx === 0 && (
              <Space wrap style={{ marginBottom: 12 }}>
                <Text>View:</Text>
                <Select
                  style={{ width: 130 }}
                  value={viewMode}
                  onChange={(v) => setViewMode(v)}
                  options={[
                    { label: "Detail", value: "detail" },
                    { label: "Summary", value: "summary" }
                  ]}
                />
                <Text>Slice:</Text>
                <Select
                  allowClear
                  style={{ width: 180 }}
                  value={sliceColumn || undefined}
                  onChange={(v) => setSliceColumn(v ?? "")}
                  options={allColumns.map((c) => ({ label: c, value: c }))}
                />
                <Input
                  style={{ width: 180 }}
                  placeholder="Slice value"
                  value={sliceValue}
                  onChange={(e) => setSliceValue(e.target.value)}
                />
                <Text>Group by:</Text>
                <Select
                  allowClear
                  style={{ width: 180 }}
                  value={groupBy || undefined}
                  onChange={(v) => setGroupBy(v ?? "")}
                  options={allColumns.map((c) => ({ label: c, value: c }))}
                />
                <Text>Sum:</Text>
                <Select
                  allowClear
                  style={{ width: 180 }}
                  value={sumColumn || undefined}
                  onChange={(v) => setSumColumn(v ?? "")}
                  options={allColumns.map((c) => ({ label: c, value: c }))}
                />
                <Button onClick={handleApplyFilter}>Load loc</Button>
              </Space>
            )}
            <JsonTable
              rows={viewMode === "summary" ? buildSummary(applySlice(item.data.rows)) : applySlice(item.data.rows)}
              pageSize={10}
            />
          </Card>
        ))}
      </Space>
    </Card>
  );
}

import { useState } from "react";
import { Button, Card, DatePicker, InputNumber, Select, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { getEtlLogs, runEtl } from "../api/endpoints";
import { displayStatus } from "../utils/status";

const { Text } = Typography;

export default function EtlPage() {
  const [running, setRunning] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [limit, setLimit] = useState(20);
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [jobName, setJobName] = useState<string | undefined>(undefined);
  const [fromTime, setFromTime] = useState<string | undefined>(undefined);
  const [toTime, setToTime] = useState<string | undefined>(undefined);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [runStatus, setRunStatus] = useState<string>("Time");

  const handleRunEtl = async () => {
    setRunning(true);
    try {
      const result = await runEtl();
      setRunStatus(`Time: ${result.elapsed_seconds}s`);
      message.success("Da chay ETL thanh cong");
      await handleLoadLogs();
    } catch (e) {
      setRunStatus("error");
      message.error(String(e));
    } finally {
      setRunning(false);
    }
  };

  const handleLoadLogs = async () => {
    setLogsLoading(true);
    try {
      const result = await getEtlLogs(limit, {
        status,
        job_name: jobName,
        from_time: fromTime,
        to_time: toTime
      });
      setLogs(
        result.rows.map((row) => ({
          LogID: row.LOGID ?? row.LogID ?? "",
          TenJob: row.TENJOB ?? row.TenJob ?? "",
          ThoiGianBD: row.THOIGIANBD ?? row.ThoiGianBD ?? "",
          ThoiGianKT: row.THOIGIANKT ?? row.ThoiGianKT ?? "",
          TrangThai: displayStatus(String(row.TRANGTHAI ?? row.TrangThai ?? "")),
          SoBanGhi: row.SOBANGHI ?? row.SoBanGhi ?? "",
          GhiChu: row.GHICHU ?? row.GhiChu ?? ""
        }))
      );
    } catch (e) {
      message.error(String(e));
    } finally {
      setLogsLoading(false);
    }
  };

  return (
    <Card
      className="page-card"
      title="ETL Control"
      extra={
        <Space wrap>
          <Button type="primary" loading={running} onClick={handleRunEtl}>
            Run ETL
          </Button>
          <Tag color={runStatus.startsWith("success") ? "green" : "default"}>{runStatus}</Tag>
        </Space>
      }
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Card size="small">
          <Space wrap>
            <Text>Limit:</Text>
            <InputNumber min={1} max={200} value={limit} onChange={(v) => setLimit(v ?? 20)} />
            <Text>Job:</Text>
            <Select
              allowClear
              placeholder="Tat ca"
              style={{ width: 180 }}
              value={jobName}
              onChange={setJobName}
              options={[
                { label: "RUN_ALL", value: "RUN_ALL" },
                { label: "LOAD_DIM_TIME", value: "LOAD_DIM_TIME" },
                { label: "LOAD_DIM_LOCATION", value: "LOAD_DIM_LOCATION" },
                { label: "LOAD_DIM_PRODUCT", value: "LOAD_DIM_PRODUCT" },
                { label: "LOAD_DIM_CUSTOMER", value: "LOAD_DIM_CUSTOMER" },
                { label: "LOAD_FACT_INVENTORY", value: "LOAD_FACT_INVENTORY" },
                { label: "LOAD_FACT_ORDER", value: "LOAD_FACT_ORDER" }
              ]}
            />
            <Text>Status:</Text>
            <Select
              allowClear
              placeholder="Tat ca"
              style={{ width: 160 }}
              value={status}
              onChange={setStatus}
              options={[
                { label: "THANH CONG", value: "THANH CONG" },
                { label: "LOI", value: "LOI" },
                { label: "SKIP", value: "SKIP" }
              ]}
            />
            <Text>From:</Text>
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              onChange={(v) => setFromTime(v ? dayjs(v).format("YYYY-MM-DDTHH:mm:ss") : undefined)}
            />
            <Text>To:</Text>
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              onChange={(v) => setToTime(v ? dayjs(v).format("YYYY-MM-DDTHH:mm:ss") : undefined)}
            />
            <Button loading={logsLoading} onClick={handleLoadLogs}>
              Load Logs
            </Button>
          </Space>

          <div style={{ marginTop: 12 }}>
            <Table
              size="small"
              rowKey={(r) => String(r.LogID)}
              pagination={{
                pageSize: 10,
                showTotal: (total) => `Total rows: ${total}`
              }}
              scroll={{ x: true }}
              rowClassName={(record) =>
                String(record.TrangThai ?? "").toUpperCase() === "LOI" ? "row-error" : ""
              }
              dataSource={logs}
              columns={[
                { title: "LogID", dataIndex: "LogID", key: "LogID" },
                { title: "TenJob", dataIndex: "TenJob", key: "TenJob" },
                { title: "ThoiGianBD", dataIndex: "ThoiGianBD", key: "ThoiGianBD" },
                { title: "ThoiGianKT", dataIndex: "ThoiGianKT", key: "ThoiGianKT" },
                { title: "TrangThai", dataIndex: "TrangThai", key: "TrangThai" },
                { title: "SoBanGhi", dataIndex: "SoBanGhi", key: "SoBanGhi" },
                { title: "GhiChu", dataIndex: "GhiChu", key: "GhiChu" }
              ]}
            />
          </div>
        </Card>
      </Space>
    </Card>
  );
}

import { useState } from "react";
import { Button, Card, Descriptions, Space, Statistic, Table, Typography, message } from "antd";
import { getDashboardSummary } from "../api/endpoints";
import type { DashboardSummary } from "../api/types";
import { displayStatus } from "../utils/status";

const { Text } = Typography;

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const result = await getDashboardSummary();
      setData(result);
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      className="page-card dashboard-card"
      title="Dashboard Summary"
      extra={
        <Button loading={loading} onClick={load}>
          Refresh
        </Button>
      }
    >
      {!data && <Text type="secondary">Click Refresh to load summary.</Text>}
      {data && (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <div className="grid-2">
            <Card>
              <Statistic title="ETL Error (24h)" value={data.etl_error_24h} />
            </Card>
            <Card>
              <Statistic title="Last RUN_ALL Status" value={displayStatus(data.last_run_all?.status)} />
            </Card>
          </div>

          <Card title="Table Counts">
            <Descriptions bordered size="small" column={1}>
              {Object.entries(data.table_counts).map(([table, count]) => (
                <Descriptions.Item key={table} label={table}>
                  {count}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>

          <Card title="Last RUN_ALL">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Job">{data.last_run_all?.job_name ?? "N/A"}</Descriptions.Item>
              <Descriptions.Item label="Status">{displayStatus(data.last_run_all?.status)}</Descriptions.Item>
              <Descriptions.Item label="Finished At">{data.last_run_all?.finished_at ?? "N/A"}</Descriptions.Item>
              <Descriptions.Item label="Note">{data.last_run_all?.note ?? "N/A"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Last LOAD_* (Row Count thuc te)">
            <Table
              size="small"
              pagination={false}
              scroll={{ x: true }}
              rowKey="job_name"
              columns={[
                { title: "Job", dataIndex: "job_name", key: "job_name" },
                { title: "Status", dataIndex: "status", key: "status", render: (value: string) => displayStatus(value) },
                { title: "Row Count", dataIndex: "row_count", key: "row_count" },
                { title: "Finished At", dataIndex: "finished_at", key: "finished_at" },
                { title: "Note", dataIndex: "note", key: "note" }
              ]}
              dataSource={data.last_load_jobs}
            />
          </Card>
        </Space>
      )}
    </Card>
  );
}

import { useState } from "react";
import { Button, Card, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { getQualityChecks } from "../api/endpoints";
import type { QualityResponse } from "../api/types";

const { Text } = Typography;

export default function QualityPage() {
  const [data, setData] = useState<QualityResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const result = await getQualityChecks();
      setData(result);
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="page-card" title="Data Quality" extra={<Button onClick={load} loading={loading}>Run Checks</Button>}>
      {!data && <Text type="secondary">Bam Run Checks de doi soat nhanh DW va nguon.</Text>}
      {data && (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div className="grid-2">
            <Card><Statistic title="Total Checks" value={data.summary.total} /></Card>
            <Card><Statistic title="OK" value={data.summary.ok} /></Card>
          </div>
          <Table
            size="small"
            rowKey="name"
            pagination={false}
            dataSource={data.checks}
            columns={[
              { title: "Check", dataIndex: "name", key: "name" },
              { title: "DW", dataIndex: "dw_value", key: "dw_value" },
              { title: "Source", dataIndex: "source_value", key: "source_value" },
              {
                title: "Result",
                dataIndex: "match",
                key: "match",
                render: (v: boolean | null) => {
                  if (v === true) return <Tag color="green">MATCH</Tag>;
                  if (v === false) return <Tag color="red">MISMATCH</Tag>;
                  return <Tag color="gold">UNAVAILABLE</Tag>;
                }
              },
              { title: "Note", dataIndex: "note", key: "note" },
              {
                title: "Error",
                dataIndex: "error",
                key: "error",
                render: (v: string | null) => v ?? "null"
              }
            ]}
          />
        </Space>
      )}
    </Card>
  );
}

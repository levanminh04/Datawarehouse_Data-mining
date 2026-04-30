import { useState } from "react";
import { Button, Card, Space, Tag, Typography, message } from "antd";
import { getHealth, getHealthDb } from "../api/endpoints";

const { Text } = Typography;

export default function HealthPage() {
  const [health, setHealth] = useState<string>("unknown");
  const [db, setDb] = useState<string>("unknown");

  const onCheckHealth = async () => {
    try {
      const r = await getHealth();
      setHealth(r.status);
    } catch (e) {
      message.error(String(e));
      setHealth("error");
    }
  };

  const onCheckDb = async () => {
    try {
      const r = await getHealthDb();
      setDb(`${r.status} (ping=${r.oracle_ping})`);
    } catch (e) {
      message.error(String(e));
      setDb("error");
    }
  };

  return (
    <Card className="page-card" title="Health Check">
      <Space direction="vertical">
        <Space>
          <Button onClick={onCheckHealth}>Check API Health</Button>
          <Tag color={health === "ok" ? "green" : "default"}>{health}</Tag>
        </Space>
        <Space>
          <Button onClick={onCheckDb}>Check Oracle Health</Button>
          <Tag color={db.startsWith("ok") ? "green" : "default"}>{db}</Tag>
        </Space>
        <Text type="secondary">API base URL: {import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}</Text>
      </Space>
    </Card>
  );
}

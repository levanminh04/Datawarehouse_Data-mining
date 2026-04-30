import { useMemo, useState } from "react";
import { DatabaseOutlined, DashboardOutlined, PlayCircleOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { Layout, Menu, Typography } from "antd";
import DashboardPage from "./pages/DashboardPage";
import EtlPage from "./pages/EtlPage";
import OlapPage from "./pages/OlapPage";
import QualityPage from "./pages/QualityPage";

const { Header, Content } = Layout;
const { Title } = Typography;

type PageKey = "dashboard" | "etl" | "olap" | "quality";

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");

  const menuItems = useMemo(
    () => [
      { key: "dashboard", icon: <DashboardOutlined />, label: "Dashboard", className: "menu-dashboard" },
      { key: "etl", icon: <PlayCircleOutlined />, label: "ETL Control" },
      { key: "olap", icon: <DatabaseOutlined />, label: "OLAP Explorer" },
      { key: "quality", icon: <SafetyCertificateOutlined />, label: "Data Quality" }
    ],
    []
  );

  return (
    <Layout>
      <Header className="app-header">
        <div className="app-shell app-header-inner">
          <div>
            <Title level={4} style={{ margin: 0, color: "#fff" }}>
              Data Warehouse
            </Title>
          </div>
          <Menu
            mode="horizontal"
            theme="dark"
            selectedKeys={[page]}
            items={menuItems}
            onClick={(e) => setPage(e.key as PageKey)}
            className="app-menu"
          />
        </div>
      </Header>
      <Content className="app-shell">
        {page === "dashboard" && <DashboardPage />}
        {page === "etl" && <EtlPage />}
        {page === "olap" && <OlapPage />}
        {page === "quality" && <QualityPage />}
      </Content>
    </Layout>
  );
}

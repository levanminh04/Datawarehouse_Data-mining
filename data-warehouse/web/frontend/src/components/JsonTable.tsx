import { Table } from "antd";

type Props = {
  rows: Array<Record<string, unknown>>;
  pageSize?: number;
};

export default function JsonTable({ rows, pageSize = 5 }: Props) {
  const columns =
    rows.length > 0
      ? Object.keys(rows[0]).map((key) => ({
          title: key,
          dataIndex: key,
          key,
          render: (value: unknown) => String(value ?? "")
        }))
      : [];

  const data = rows.map((row, idx) => ({ ...row, __key: idx }));

  return (
    <Table
      columns={columns}
      dataSource={data}
      rowKey="__key"
      pagination={{
        pageSize,
        showTotal: (total) => `Total rows: ${total}`
      }}
      scroll={{ x: true }}
      size="small"
    />
  );
}

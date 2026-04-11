---
language: typescript
domain: frontend
type: pattern
title: Dashboard Chart Panel
archetype: dashboard
pattern_scope: component
semantic_role: chart
generation_priority: 2
tags: dashboard, chart, visualization, react, typescript, recharts
---

# Dashboard Chart Panel

A reusable chart panel component for dashboards with title, controls, and responsive chart area.

## Component Structure

```tsx
interface ChartPanelProps {
  title: string;
  description?: string;
  timeRange?: "24h" | "7d" | "30d" | "90d";
  onTimeRangeChange?: (range: string) => void;
  children: React.ReactNode;
  actions?: { label: string; onClick: () => void; icon?: React.ReactNode }[];
}

export function ChartPanel({
  title,
  description,
  timeRange,
  onTimeRangeChange,
  children,
  actions,
}: ChartPanelProps) {
  const timeRanges = [
    { label: "24H", value: "24h" },
    { label: "7D", value: "7d" },
    { label: "30D", value: "30d" },
    { label: "90D", value: "90d" },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {description && (
            <p className="text-sm text-gray-500 mt-1">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {timeRange && onTimeRangeChange && (
            <div className="flex bg-gray-100 rounded-lg p-1">
              {timeRanges.map((range) => (
                <button
                  key={range.value}
                  onClick={() => onTimeRangeChange(range.value)}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    timeRange === range.value
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>
          )}
          {actions && (
            <div className="flex gap-1">
              {actions.map((action, i) => (
                <button
                  key={i}
                  onClick={action.onClick}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                  title={action.label}
                >
                  {action.icon}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chart Area */}
      <div className="h-64 sm:h-80">{children}</div>
    </div>
  );
}
```

## Example Usage with Recharts

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

<ChartPanel
  title="Revenue Over Time"
  description="Daily revenue for the selected period"
  timeRange={timeRange}
  onTimeRangeChange={setTimeRange}
  actions={[
    { label: "Download", onClick: handleDownload, icon: <Download className="w-4 h-4" /> },
    { label: "Fullscreen", onClick: handleFullscreen, icon: <Maximize className="w-4 h-4" /> },
  ]}
>
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={chartData}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
      <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
      <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
      <Tooltip
        contentStyle={{
          backgroundColor: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: "8px",
        }}
      />
      <Line
        type="monotone"
        dataKey="revenue"
        stroke="#3b82f6"
        strokeWidth={2}
        dot={false}
      />
    </LineChart>
  </ResponsiveContainer>
</ChartPanel>
```

## Accessibility Notes

- Semantic heading (h3) for title
- Tooltips provide context for chart data
- Controls have visible focus states

## Related Patterns

- Dashboard KPI Strip (for summary metrics)
- Data Table (for detailed data view)

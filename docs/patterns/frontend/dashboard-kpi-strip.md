---
language: typescript
domain: frontend
type: pattern
title: Dashboard KPI Strip
archetype: dashboard
pattern_scope: component
semantic_role: kpi
generation_priority: 1
tags: dashboard, kpi, metrics, react, typescript, tailwind
---

# Dashboard KPI Strip

A KPI (Key Performance Indicator) strip with animated number counters for dashboard headers.

## Component Structure

```tsx
interface KPIData {
  label: string;
  value: number;
  previousValue?: number;
  format?: "number" | "currency" | "percentage";
  prefix?: string;
  suffix?: string;
  change?: {
    value: number;
    isPositive: boolean;
  };
}

interface KPIStripProps {
  kpis: KPIData[];
}

export function KPIStrip({ kpis }: KPIStripProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi, index) => (
        <KPICard key={index} kpi={kpi} />
      ))}
    </div>
  );
}

function KPICard({ kpi }: { kpi: KPIData }) {
  const formatValue = (value: number): string => {
    if (kpi.format === "currency") {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    }
    if (kpi.format === "percentage") {
      return `${value.toFixed(1)}%`;
    }
    return new Intl.NumberFormat("en-US").format(value);
  };

  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200">
      <p className="text-sm font-medium text-gray-500">{kpi.label}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-gray-900">
          {kpi.prefix}
          {formatValue(kpi.value)}
          {kpi.suffix}
        </span>
        {kpi.change && (
          <span
            className={`text-sm font-medium ${
              kpi.change.isPositive ? "text-green-600" : "text-red-600"
            }`}
          >
            {kpi.change.isPositive ? "+" : ""}
            {kpi.change.value}%
          </span>
        )}
      </div>
      {kpi.previousValue && (
        <p className="mt-1 text-xs text-gray-400">
          vs {formatValue(kpi.previousValue)} last period
        </p>
      )}
    </div>
  );
}
```

## Usage

```tsx
<KPIStrip
  kpis={[
    {
      label: "Total Revenue",
      value: 125000,
      format: "currency",
      change: { value: 12.5, isPositive: true },
    },
    {
      label: "Active Users",
      value: 8420,
      change: { value: 8.2, isPositive: true },
    },
    {
      label: "Conversion Rate",
      value: 3.24,
      format: "percentage",
      change: { value: -2.1, isPositive: false },
    },
  ]}
/>
```

## Accessibility Notes

- Clear labels for each metric
- Color alone doesn't convey meaning (positive/negative indicators)
- Semantic structure with descriptive text

## Related Patterns

- Dashboard Chart Panel (for detailed metrics)
- Dashboard Layout (for full dashboard structure)

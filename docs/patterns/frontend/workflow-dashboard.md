---
language: typescript
domain: frontend
type: pattern
title: Dashboard Generation Flow
archetype: dashboard
pattern_scope: workflow
semantic_role: workflow
generation_priority: 2
tags: workflow, dashboard, generation, process, data-viz
---

# Dashboard Generation Flow

A retrieval-first workflow for generating data-rich admin dashboards.

## Phase 1: Retrieve Patterns

```markdown
1. Search `knowledge.pattern_search` for:
   - archetype: "dashboard"
   - pattern_scope: "component"
   - Query: "KPI strip metrics"

2. Search `knowledge.pattern_search` for:
   - archetype: "dashboard"
   - pattern_scope: "component"
   - Query: "chart panel time range"

3. Retrieve `knowledge.task_patterns` for:
   - Query: "dashboard generation"
   - Top 3 similar past tasks

4. Search `knowledge.pattern_search` for:
   - pattern_scope: "media" or "effect"
   - Query: "premium visual effect dashboard motion-safe"
```

## Phase 2: Select Components

| Priority | Component | Semantic Role | Library |
|----------|-----------|---------------|---------|
| 1 | Navigation Header | navigation | Custom |
| 2 | KPI Strip | kpi | Custom |
| 3 | Chart Panel | chart | Recharts |
| 4 | Data Table | table | TanStack Table |
| 5 | Filter Bar | form | Custom |
| 6 | Date Picker | form | Custom/shadcn |
| 7 | Sidebar | sidebar | Custom |

## Phase 3: Layout Strategy

```
┌─────────────────────────────────┐
│        Navigation Header         │
├──────────┬──────────────────────┤
│          │    KPI Strip         │
│ Sidebar  ├──────────────────────┤
│          │    Chart Panel 1     │
│          ├──────────────────────┤
│          │    Chart Panel 2     │
│          ├──────────────────────┤
│          │    Data Table        │
└──────────┴──────────────────────┘
```

## Phase 4: Data Flow

```tsx
// 1. Define types for API data
interface DashboardData {
  kpis: KPIData[];
  charts: ChartData[];
  tableData: TableRow[];
}

// 2. Fetch data with SWR or React Query
const { data, error, isLoading } = useSWR<DashboardData>(
  "/api/dashboard",
  fetcher
);

// 3. Render with loading states
if (isLoading) return <DashboardSkeleton />;
if (error) return <ErrorState />;

// 4. Pass data to components
return (
  <DashboardLayout>
    <KPIStrip kpis={data.kpis} />
    <ChartPanel title="Revenue">
      <RevenueChart data={data.charts} />
    </ChartPanel>
  </DashboardLayout>
);
```

## Phase 5: Real-time Updates

```tsx
// For real-time dashboards
useEffect(() => {
  const interval = setInterval(() => {
    mutate("/api/dashboard");
  }, 30000); // Refresh every 30s

  return () => clearInterval(interval);
}, []);
```

## Phase 6: Validate + Evidence

- [ ] Responsive checks at mobile/tablet/desktop
- [ ] Accessibility checks completed (automated + keyboard pass)
- [ ] Reduced-motion behavior verified
- [ ] Runtime harness defined (preview command + local URL)
- [ ] Tailwind quality reviewed
- [ ] Evidence package collected (checklist + screenshots + command outputs + manifest)
- [ ] Design/media enhancement pass completed where appropriate

Log successful workflow outcomes:

```bash
python scripts/log-task-success.py \
  --description "Dashboard generation with QA evidence package" \
  --approach "Retrieval-first dashboard patterns and QA workflow" \
  --outcome "Data dashboard validated for responsiveness, accessibility, and consistency" \
  --tools "knowledge.pattern_search,knowledge.task_patterns" \
  --phase "P63"
```

## Related Patterns

- Landing Page Generation Flow (for marketing sites)
- KPI Strip Component (for metrics display)
- Chart Panel Component (for visualizations)
- Frontend QA Evidence Workflow

# Dashboards

Prompts and scaffold guidance for data-rich admin interfaces.

---

## Purpose

Dashboards present **data and controls** for managing systems, viewing analytics, or performing administrative tasks. They prioritize information density and quick actions.

---

## Layout Patterns

### Standard Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  Sidebar        │  Header                           │
│  - Navigation   │  - Search + Notifications + User  │
│  - Collapsible  │                                   │
├─────────────────┼───────────────────────────────────┤
│                 │                                   │
│                 │  Main Content Area                │
│                 │  ┌─────────────────────────────┐  │
│                 │  │  KPI Cards (4)              │  │
│                 │  │  [KPI] [KPI] [KPI] [KPI]    │  │
│                 │  └─────────────────────────────┘  │
│                 │  ┌─────────────────────────────┐  │
│                 │  │  Chart: Primary Metric      │  │
│                 │  └─────────────────────────────┘  │
│                 │  ┌─────────────┐ ┌──────────────┐ │
│                 │  │  Recent     │ │  Status      │ │
│                 │  │  Activity   │ │  Overview    │ │
│                 │  └─────────────┘ └──────────────┘ │
│                 │                                   │
└─────────────────┴───────────────────────────────────┘
```

### Responsive Behavior

**Desktop:**
- Fixed or collapsible sidebar
- Multi-column KPI grid
- Side-by-side charts

**Tablet:**
- Collapsible sidebar
- 2-column KPI grid
- Stacked charts

**Mobile:**
- Hidden sidebar (hamburger menu)
- Single column KPIs
- Full-width charts

---

## Core Components

### 1. KPI Cards

**Prompt:**

```markdown
TASK: Create KPI metric cards for dashboard header.

CONTEXT:
- Metrics: [Revenue, Users, Conversion, Churn]
- Formats: [currency, number, percent, percent]
- Trends: [+12%, +5%, -2%, -0.5%]

FORMAT:
- KpiCard.tsx
- Props: title, value, change, format, trend
- Optional: sparkline mini-chart

CONSTRAINTS:
- Large, scannable numbers
- Color-coded trends (green/red)
- Currency formatting for money
- Responsive: 1×4 → 2×2 → 1×4 grid
```

### 2. Charts

**Common Types:**
- Line chart (trends over time)
- Bar chart (comparisons)
- Pie/donut (proportions)
- Area chart (cumulative)

**Prompt:**

```markdown
TASK: Build a primary chart component for dashboard.

CONTEXT:
- Chart type: [line/bar/area]
- Data: [time-series or categories]
- Height: 300-400px
- Interactive: [tooltip on hover]

FORMAT:
- ChartWidget.tsx
- Props: data, title, type
- Uses recharts or chart library

CONSTRAINTS:
- Responsive width (100% container)
- Loading state
- Empty state
- Color accessible (not just color to convey meaning)
```

### 3. Data Tables

**Features:**
- Sortable columns
- Search/filter
- Pagination
- Row actions
- Selection (checkboxes)

**Prompt:**

```markdown
TASK: Create a data table with sorting and pagination.

CONTEXT:
- Columns: [name, status, date, amount, actions]
- Rows per page: 10, 25, 50
- Sortable: [name, date, amount]
- Actions: [view, edit, delete]

FORMAT:
- DataTable.tsx
- TableHeader.tsx (sort controls)
- TableRow.tsx
- Pagination.tsx

CONSTRAINTS:
- Header row sticky on scroll
- Responsive: horizontal scroll or card view
- Empty state with CTA
- Loading skeleton
- Keyboard navigation (arrow keys)
```

### 4. Sidebar Navigation

**Structure:**
- Logo/brand
- Main nav items (with icons)
- Section dividers
- Collapse/expand control

**Prompt:**

```markdown
TASK: Build a collapsible sidebar navigation.

CONTEXT:
- Nav items: [Dashboard, Users, Orders, Reports, Settings]
- Active state: highlighted
- Collapse: to icon-only mode

FORMAT:
- Sidebar.tsx
- NavItem.tsx
- Collapse toggle

CONSTRAINTS:
- Keyboard navigable
- aria-current for active item
- Tooltip on collapsed items
- Smooth collapse transition
- Mobile: slide-out drawer
```

### 5. Header

**Elements:**
- Search bar
- Notifications bell
- User menu (avatar + dropdown)
- Mobile menu toggle

---

## State Management Patterns

### Dashboard Data Flow

```
DashboardPage
├── useDashboardData hook (fetches data)
├── KpiSection (receives KPI data)
├── ChartSection (receives chart data)
└── RecentActivity (receives activity feed)
```

### Loading States

```tsx
// Skeleton loading for dashboard
function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}
```

---

## Design Considerations

### Information Density

- **High density:** Admin tools, analytics
- **Medium density:** Project management
- **Lower density:** Simple monitoring

### Color Usage

| Use | Color | Example |
|-----|-------|---------|
| Success | Green | Active status, positive trend |
| Warning | Yellow | Warning state, attention needed |
| Error | Red | Error state, critical issue |
| Info | Blue | Information, neutral trend |
| Neutral | Gray | Inactive, default state |

### Typography Scale

- **Metric values:** 24-32px (large, scannable)
- **Section headers:** 18-20px
- **Table text:** 14px
- **Labels/meta:** 12px

---

## Accessibility for Dashboards

### Data Visualization

- Don't rely on color alone (add patterns/icons)
- Provide data tables as alternative
- Ensure sufficient contrast
- Make charts keyboard navigable

### Tables

```tsx
// Accessible table
<table>
  <caption>User activity summary</caption>
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">John Doe</th>
      <td>Active</td>
    </tr>
  </tbody>
</table>
```

### Focus Management

- Skip link to main content
- Focus trap in modals
- Clear focus indicators
- Logical tab order

---

## Example File Structure

```
src/
├── layouts/
│   └── DashboardLayout.tsx
├── pages/
│   ├── dashboard/
│   │   ├── index.tsx
│   │   ├── users.tsx
│   │   ├── orders.tsx
│   │   └── settings.tsx
├── components/
│   ├── dashboard/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── KpiCard.tsx
│   │   ├── KpiSection.tsx
│   │   ├── ChartWidget.tsx
│   │   ├── DataTable.tsx
│   │   ├── RecentActivity.tsx
│   │   └── NotificationBell.tsx
│   └── ui/
│       ├── Skeleton.tsx
│       ├── Badge.tsx
│       └── Avatar.tsx
├── hooks/
│   ├── useDashboardData.ts
│   └── useTableSort.ts
└── lib/
    └── formatters.ts
```

---

## Validation Checklist

- [ ] Data loads efficiently (pagination, lazy loading)
- [ ] Loading states for all async data
- [ ] Error states with retry
- [ ] Responsive layout works on all sizes
- [ ] Keyboard navigation functional
- [ ] Charts have text alternatives
- [ ] Real-time updates (if applicable) don't cause layout shift
- [ ] Dark mode support (optional but recommended)

---

## References

- [Dashboard Design Best Practices](https://www.nngroup.com/articles/dashboard-design/)
- [Data Visualization Accessibility](https://www.w3.org/WAI/tutorials/images/complex/)
- [Material Design Dashboard](https://m3.material.io/components)

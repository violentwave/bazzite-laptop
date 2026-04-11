---
language: typescript
domain: frontend
type: pattern
title: SVG to Component Workflow
archetype: landing-page
pattern_scope: workflow
semantic_role: asset
generation_priority: 2
tags: svg, workflow, components, react, typescript
---

# SVG to Component Workflow

A workflow for converting SVG assets to React components with proper accessibility and styling.

## SVG Component Template

```tsx
interface IconProps {
  className?: string;
  size?: number | string;
  color?: string;
  ariaLabel?: string;
}

export function IconCheck({
  className = "",
  size = 24,
  color = "currentColor",
  ariaLabel,
}: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden={!ariaLabel}
      aria-label={ariaLabel}
      role={ariaLabel ? "img" : undefined}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
```

## SVGO Config

```js
// svgo.config.js
module.exports = {
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          removeViewBox: false,
          removeTitle: false,
        },
      },
    },
    "removeDimensions", // Let component control size
    {
      name: "addAttributesToSVGElement",
      params: {
        attributes: [{ xmlns: "http://www.w3.org/2000/svg" }],
      },
    },
  ],
};
```

## Automation Script

```bash
#!/bin/bash
# scripts/convert-svgs.sh

INPUT_DIR="assets/icons"
OUTPUT_DIR="src/components/icons"

for file in $INPUT_DIR/*.svg; do
  filename=$(basename "$file" .svg)
  componentName="Icon$(echo $filename | sed 's/-\([a-z]\)/\u\1/g' | sed 's/^\([a-z]\)/\u\1/')"

  npx @svgr/cli \
    --typescript \
    --icon \
    --replace-attr-values "#000=currentColor" \
    --out-dir "$OUTPUT_DIR" \
    "$file"

  mv "$OUTPUT_DIR/$filename.tsx" "$OUTPUT_DIR/$componentName.tsx"
done
```

## Icon Library Pattern

```tsx
// components/icons/index.ts
export { IconCheck } from "./IconCheck";
export { IconClose } from "./IconClose";
export { IconArrowRight } from "./IconArrowRight";
// ... etc

// Usage
import { IconCheck } from "@/components/icons";

<IconCheck size={20} color="green" ariaLabel="Completed" />
```

## Accessibility Rules

1. **Decorative icons**: `aria-hidden="true"`
2. **Standalone icons**: `aria-label` and `role="img"`
3. **Inside buttons**: `aria-hidden` on icon, text on button
4. **No title**: Remove SVG title, use aria-label instead

## Related Patterns

- Asset Naming Conventions (for file organization)
- Feature Grid (for icon usage examples)

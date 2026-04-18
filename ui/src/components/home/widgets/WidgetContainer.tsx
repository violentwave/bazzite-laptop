"use client";

import { ReactNode, useCallback } from "react";

type WidgetContainerProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onRemove?: () => void;
  onConfigure?: () => void;
  className?: string;
};

export function WidgetContainer({
  title,
  subtitle,
  children,
  onRemove,
  onConfigure,
  className = "",
}: WidgetContainerProps) {
  const handleRemove = useCallback(() => {
    onRemove?.();
  }, [onRemove]);

  const handleConfigure = useCallback(() => {
    onConfigure?.();
  }, [onConfigure]);

  return (
    <section
      className={`rounded-xl p-4 border border-base-4 ${className}`}
      style={{
        background: "var(--base-2)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onConfigure && (
            <button
              onClick={handleConfigure}
              className="px-2 py-1 rounded text-xs transition-colors hover:bg-base-1"
              style={{
                border: "1px solid var(--base-4)",
                color: "var(--text-tertiary)",
              }}
            >
              Configure
            </button>
          )}
          {onRemove && (
            <button
              onClick={handleRemove}
              className="px-2 py-1 rounded text-xs text-danger hover:bg-danger/10"
              style={{
                border: "1px solid var(--base-4)",
                color: "var(--danger)",
              }}
            >
              Remove
            </button>
          )}
        </div>
      </div>
      <div>{children}</div>
    </section>
  );
}

"use client";

import { useShell } from "./ShellContext";

interface Notification {
  id: string;
  type: "critical" | "high" | "medium" | "low";
  title: string;
  message: string;
  timestamp: string;
  action?: {
    label: string;
    href?: string;
  };
}

const notifications: Notification[] = [];

export function NotificationsPanel() {
  const { isNotificationsOpen, toggleNotifications } = useShell();

  if (!isNotificationsOpen) return null;

  const criticalCount = notifications.filter(
    (n) => n.type === "critical" || n.type === "high"
  ).length;

  return (
    <div
      className="fixed right-0 top-[48px] bottom-0 w-[360px] z-40 flex flex-col"
      style={{
        background: "var(--base-02)",
        borderLeft: "1px solid var(--base-04)",
        boxShadow: "var(--shadow-xl)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--base-04)" }}
      >
        <div className="flex items-center gap-2">
          <BellIcon />
          <span
            className="font-medium"
            style={{ color: "var(--text-primary)" }}
          >
            Notifications
          </span>
          {criticalCount > 0 && (
            <span
              className="px-2 py-0.5 rounded-full text-xs"
              style={{
                background: "var(--danger)",
                color: "white",
              }}
            >
              {criticalCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleNotifications}
            className="p-1.5 rounded hover:bg-base-03 transition-colors"
            style={{ color: "var(--text-tertiary)" }}
            title="Close"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      {/* Notification List */}
      <div className="flex-1 overflow-y-auto">
        {notifications.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center h-full px-4 text-center"
            style={{ color: "var(--text-secondary)" }}
          >
            <BellIcon className="mb-2 opacity-50" />
            <p>No notifications</p>
            <p className="text-xs mt-2" style={{ color: "var(--text-tertiary)" }}>
              Real-time notification streaming is not wired in this build.
            </p>
          </div>
        ) : (
          notifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
            />
          ))
        )}
      </div>

      <div
        className="px-4 py-3 border-t text-xs"
        style={{ borderColor: "var(--base-04)", color: "var(--text-tertiary)" }}
      >
        When backend event feeds are available, notifications will appear here.
      </div>
    </div>
  );
}

function NotificationItem({ notification }: { notification: Notification }) {
  const getTypeStyles = (type: Notification["type"]) => {
    switch (type) {
      case "critical":
        return {
          icon: "🚨",
          borderColor: "var(--danger)",
          bgColor: "rgba(239, 68, 68, 0.1)",
        };
      case "high":
        return {
          icon: "⚠️",
          borderColor: "var(--warning)",
          bgColor: "rgba(245, 158, 11, 0.1)",
        };
      case "medium":
        return {
          icon: "ℹ️",
          borderColor: "var(--info)",
          bgColor: "transparent",
        };
      default:
        return {
          icon: "💬",
          borderColor: "transparent",
          bgColor: "transparent",
        };
    }
  };

  const styles = getTypeStyles(notification.type);

  return (
    <div
      className="px-4 py-3 border-l-[3px] hover:bg-base-03 transition-colors cursor-pointer"
      style={{
        borderColor: styles.borderColor,
        background: styles.bgColor,
      }}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg shrink-0">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4
              className="font-medium text-sm truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {notification.title}
            </h4>
            <span
              className="text-xs shrink-0"
              style={{ color: "var(--text-tertiary)" }}
            >
              {notification.timestamp}
            </span>
          </div>
          <p
            className="text-sm mt-0.5"
            style={{ color: "var(--text-secondary)" }}
          >
            {notification.message}
          </p>
          {notification.action && (
            <button
              className="text-sm mt-2 hover:underline"
              style={{ color: "var(--accent-primary)" }}
            >
              {notification.action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* Icon Components */

function BellIcon({ className }: { className?: string }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ color: "var(--text-secondary)" }}
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

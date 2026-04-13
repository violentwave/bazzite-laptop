"use client";

import { useState, createContext, useContext, ReactNode } from "react";

interface ShellContextType {
  /** Whether the icon rail is expanded */
  isRailExpanded: boolean;
  /** Toggle the icon rail */
  toggleRail: () => void;
  /** Current active panel */
  activePanel: string;
  /** Set the active panel */
  setActivePanel: (panel: string) => void;
  /** Whether command palette is open */
  isCommandPaletteOpen: boolean;
  /** Open command palette */
  openCommandPalette: () => void;
  /** Close command palette */
  closeCommandPalette: () => void;
  /** Whether notifications panel is open */
  isNotificationsOpen: boolean;
  /** Toggle notifications panel */
  toggleNotifications: () => void;
  /** Audit log for privileged panels */
  auditLog: AuditEntry[];
  /** Add audit entry */
  addAuditEntry: (entry: Omit<AuditEntry, "timestamp">) => void;
}

interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  target?: string;
  timestamp: Date;
}

const ShellContext = createContext<ShellContextType | undefined>(undefined);

export function ShellProvider({ children }: { children: ReactNode }) {
  const [isRailExpanded, setIsRailExpanded] = useState(false);
  const [activePanel, setActivePanel] = useState("chat");
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);

  const toggleRail = () => setIsRailExpanded((prev) => !prev);

  const openCommandPalette = () => {
    setIsCommandPaletteOpen(true);
    setIsNotificationsOpen(false);
  };

  const closeCommandPalette = () => setIsCommandPaletteOpen(false);

  const toggleNotifications = () => {
    setIsNotificationsOpen((prev) => !prev);
    setIsCommandPaletteOpen(false);
  };

  const addAuditEntry = (entry: Omit<AuditEntry, "timestamp">) => {
    setAuditLog((prev) => [
      {
        ...entry,
        timestamp: new Date(),
      },
      ...prev.slice(0, 99), // Keep last 100 entries
    ]);
  };

  return (
    <ShellContext.Provider
      value={{
        isRailExpanded,
        toggleRail,
        activePanel,
        setActivePanel,
        isCommandPaletteOpen,
        openCommandPalette,
        closeCommandPalette,
        isNotificationsOpen,
        toggleNotifications,
        auditLog,
        addAuditEntry,
      }}
    >
      {children}
    </ShellContext.Provider>
  );
}

export function useShell() {
  const context = useContext(ShellContext);
  if (context === undefined) {
    throw new Error("useShell must be used within a ShellProvider");
  }
  return context;
}

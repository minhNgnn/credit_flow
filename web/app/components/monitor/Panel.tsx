"use client";

import { useState, type ReactNode } from "react";

import { useI18n } from "../../lib/i18n";

interface Props {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  defaultCollapsed?: boolean;
}

export default function Panel({ title, icon, children, defaultCollapsed = false }: Props) {
  const { tv } = useI18n();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  return (
    <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <header className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {icon}
          {tv(title)}
        </h3>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground"
          aria-label={collapsed ? tv("Mở rộng") : tv("Thu gọn")}
        >
          {collapsed ? tv("Mở rộng") : tv("Thu gọn")}
        </button>
      </header>
      {!collapsed && <div className="space-y-3">{children}</div>}
    </section>
  );
}
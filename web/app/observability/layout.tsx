import Link from "next/link";
import type { ReactNode } from "react";

const TABS = [
  { href: "/observability/status", label: "Tình trạng" },
  { href: "/observability/traces", label: "Vết chạy" },
  { href: "/observability/decisions", label: "Quyết định" },
  { href: "/observability/collaboration", label: "Phân luồng" },
] as const;

export default function ObservabilityLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card px-6 py-3">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
          ← Trở về
        </Link>
        <h1 className="mt-1 text-lg font-semibold">Quan sát đa tác nhân</h1>
      </header>
      <nav className="flex gap-4 border-b border-border px-6">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="border-b-2 border-transparent px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            {t.label}
          </Link>
        ))}
      </nav>
      <main className="px-6 py-4">{children}</main>
    </div>
  );
}
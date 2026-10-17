import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mock Audit Agent",
  description: "A skeptical SOC 2 Type II mock auditor over a synthetic company. Readiness forecast, not an audit opinion.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="font-semibold">
              Mock Audit Agent <span className="font-normal text-slate-500">· Ledgerly (synthetic)</span>
            </Link>
            <span className="text-xs text-slate-500">SOC 2 Type II readiness forecast · not an audit opinion</span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Breach Analytics GenAI Platform",
  description: "Portfolio dashboard for breach analytics, detections, incidents, and summaries"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <div className="topbar-inner">
              <Link className="brand" href="/">
                <span className="brand-name">Breach Analytics GenAI</span>
                <span className="brand-subtitle">Security operations portfolio dashboard</span>
              </Link>
              <nav className="nav-links" aria-label="Primary navigation">
                <Link href="/#workflow">Workflow</Link>
                <Link href="/#events">Events</Link>
                <Link href="/#alerts">Alerts</Link>
                <Link href="/#incidents">Incidents</Link>
              </nav>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

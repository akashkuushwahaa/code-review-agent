import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Review Agent — Dashboard",
  description: "Security review findings and evaluation metrics for the scoped PR review agent.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <Link href="/" className="brand">
              <span className="lock" aria-hidden>🔒</span>
              <span>
                Review Agent
                <small>security · scoped</small>
              </span>
            </Link>
            <Nav />
          </header>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}

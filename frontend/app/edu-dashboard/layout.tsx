import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "../globals.css";

/**
 * Figma design tokens for Educational Dashboard (node 1:13009)
 * Source: General-playground file — Figma MCP get_variable_defs
 */
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-edu",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dashboard — Educational Platform",
  description: "Schedule, tests, and homework for students.",
};

export default function EduDashboardLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div
      className={`${plusJakarta.variable} ${plusJakarta.className} min-h-screen bg-[#0f0f0f] text-white antialiased`}
      style={
        {
          "--edu-bg-primary": "#0f0f0f",
          "--edu-bg-secondary": "#212121",
          "--edu-fill-inverted": "#ffffff",
          "--edu-text-title": "#ffffff",
          "--edu-text-body": "#bcbdbd",
          "--edu-text-active": "#3592fd",
          "--edu-text-inactive": "#848484",
          "--edu-border": "#2e2e2e",
          "--edu-radius-xs": "8px",
          "--edu-radius-sm": "12px",
          "--edu-radius-base": "16px",
          "--edu-radius-lg": "24px",
          "--edu-spacing-2": "4px",
          "--edu-spacing-4": "8px",
          "--edu-spacing-6": "12px",
          "--edu-spacing-8": "16px",
          "--edu-spacing-10": "20px",
          "--edu-spacing-11": "24px",
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  );
}

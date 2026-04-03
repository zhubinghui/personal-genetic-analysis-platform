import type { Metadata } from "next";
import { Inter } from "next/font/google";
import ErrorBoundary from "@/components/ErrorBoundary";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "基因抗衰老分析平台",
  description: "基于 DNA 甲基化数据的个性化抗衰老分析",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body>
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}

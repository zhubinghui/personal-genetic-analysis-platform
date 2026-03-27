import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "基因抗衰老分析平台",
  description: "基于 DNA 甲基化数据的个性化抗衰老分析",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

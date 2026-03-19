import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Noto_Sans_SC, Noto_Serif_SC } from "next/font/google";
import "./globals.css";

const bodyFont = Noto_Sans_SC({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "700"]
});

const displayFont = Noto_Serif_SC({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "600", "700"]
});

export const metadata: Metadata = {
  title: "引路虾研究工作台",
  description: "面向科研新人的课题组协作式研究导航工作台。",
  icons: {
    icon: "/guideclaw-logo.png"
  }
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN" className={`${bodyFont.variable} ${displayFont.variable}`}>
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"] });

export const metadata: Metadata = {
  title: "IFRS 17 Pro | Enterprise Insurance Automation",
  description: "Professional IFRS 17 Automation System for Kazakhstan Insurance Market - Big Four Quality",
  keywords: ["IFRS 17", "Insurance", "Kazakhstan", "Actuarial", "SaaS", "Automation"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={inter.className}>
        {children}
      </body>
    </html>
  );
}

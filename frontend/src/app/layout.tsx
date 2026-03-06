import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "bioAF",
  description: "Computational Biology Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">{children}</body>
    </html>
  );
}

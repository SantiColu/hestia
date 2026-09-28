import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hestia",
  description: "Thermal control system preliminary design for medium satellites.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}

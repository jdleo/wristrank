import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WristRank - the blind watch ranking game",
  description:
    "Two watches enter. You pick a winner before the brand, model and price are revealed. Elo does the rest - giant-killings pay out big. Build your watch list.",
};

export const viewport: Viewport = {
  themeColor: "#08080c",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

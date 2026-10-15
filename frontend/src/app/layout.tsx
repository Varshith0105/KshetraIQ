import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "KshetraIQ | Know Your Land. Grow With Confidence.",
  description:
    "AI-powered agricultural decision-support platform for Indian farmers. Verified crop recommendations using certified soil lab data and real-time agro-meteorological observations.",
  keywords: "crop recommendation, soil health, agriculture AI, Indian farming, Telugu farming",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}

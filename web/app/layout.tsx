import type { Metadata } from "next";
import { Geist, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

// All-technical type system — reads as "institutional financial software":
//   - IBM Plex Sans (display, 500-600) for headlines + section headings
//   - Geist Sans for body / paragraph prose
//   - IBM Plex Mono for numbers, labels, data chrome
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "MacroHero",
  description: "A Clerk-authenticated MacroHero workspace with streaming LLM chat.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${geistSans.variable} ${plexMono.variable} ${plexSans.variable} h-full antialiased dark`}
      >
        <body className="min-h-full flex flex-col">{children}</body>
      </html>
    </ClerkProvider>
  );
}

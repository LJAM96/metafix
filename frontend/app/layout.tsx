import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MetaFix - Plex Library Management",
  description: "Comprehensive Plex library management tool for artwork and edition metadata",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <header className="border-b">
            <div className="container mx-auto px-4 py-4">
              <nav className="flex items-center justify-between">
                <div className="flex items-center space-x-6">
                  <Link href="/" className="text-xl font-bold">
                    MetaFix
                  </Link>
                  <div className="flex items-center space-x-4">
                    <Link href="/" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      Dashboard
                    </Link>
                    <Link href="/scan" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      Scan
                    </Link>
                    <Link href="/scan/history" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      History
                    </Link>
                    <Link href="/edition" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      Edition
                    </Link>
                    <Link href="/issues" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      Issues
                    </Link>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <Link href="/settings" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                    Settings
                  </Link>
                </div>
              </nav>
            </div>
          </header>
          <main className="container mx-auto px-4 py-8">
            {children}
          </main>
        </div>
        <Toaster />
      </body>
    </html>
  );
}

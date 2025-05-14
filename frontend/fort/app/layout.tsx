import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { MyRuntimeProvider } from "@/app/MyRuntimeProvider";
import { Toaster } from "sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});


export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <MyRuntimeProvider>
      <html lang="en">
        <body>
          {children}
          <Toaster position="top-right" richColors />
        </body>
      </html>
    </MyRuntimeProvider>
  );
}

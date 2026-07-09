import type { ReactNode } from "react";
import Navbar from "./Navbar";
import Footer from "./Footer";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-[2000px] flex-1 px-5 sm:px-7 py-6">{children}</main>
      <Footer />
    </div>
  );
}

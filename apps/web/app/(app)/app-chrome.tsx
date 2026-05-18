"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type ChromeState = {
  sidebarOpen: boolean;
  newsOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;
  openNews: () => void;
  closeNews: () => void;
  toggleNews: () => void;
};

const Ctx = createContext<ChromeState | null>(null);

export function AppChromeProvider({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [newsOpen, setNewsOpen] = useState(false);

  // Lock body scroll while any drawer is open on mobile.
  useEffect(() => {
    const anyOpen = sidebarOpen || newsOpen;
    if (!anyOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [sidebarOpen, newsOpen]);

  // When the viewport grows past a drawer's breakpoint the drawer turns into a
  // permanent rail (sidebar at lg/1024, news at xl/1280) and CSS hides the
  // drawer element. The open state would otherwise stay `true`, leaving the
  // body scroll-locked. Reset it on the matchMedia change so the lock effect
  // above re-runs and releases.
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const handler = () => {
      if (mql.matches) setSidebarOpen(false);
    };
    handler();
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1280px)");
    const handler = () => {
      if (mql.matches) setNewsOpen(false);
    };
    handler();
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  // Close on Escape.
  useEffect(() => {
    if (!sidebarOpen && !newsOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSidebarOpen(false);
        setNewsOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen, newsOpen]);

  const openSidebar = useCallback(() => setSidebarOpen(true), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);
  const openNews = useCallback(() => setNewsOpen(true), []);
  const closeNews = useCallback(() => setNewsOpen(false), []);
  const toggleNews = useCallback(() => setNewsOpen((v) => !v), []);

  return (
    <Ctx.Provider
      value={{
        sidebarOpen,
        newsOpen,
        openSidebar,
        closeSidebar,
        toggleSidebar,
        openNews,
        closeNews,
        toggleNews,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAppChrome(): ChromeState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppChrome must be used within AppChromeProvider");
  return ctx;
}

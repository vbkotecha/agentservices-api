"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "light" | "system" | "dark";

const STORAGE_KEY = "yappa-ops-theme";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  mounted: boolean;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  setTheme: () => {},
  mounted: false,
});

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  const resolved = theme === "system" ? getSystemTheme() : theme;
  document.documentElement.classList.toggle("dark", resolved === "dark");
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
    const initial: Theme =
      stored && ["light", "system", "dark"].includes(stored)
        ? stored
        : "light";
    setThemeState(initial);
    applyTheme(initial);
    setMounted(true);

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const current = localStorage.getItem(STORAGE_KEY) as Theme | null;
      if (!current || current === "system") applyTheme("system");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setTheme = (next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, mounted }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeToggle() {
  const { theme, setTheme, mounted } = useTheme();

  if (!mounted) {
    return (
      <div className="h-7 w-[148px] rounded-lg border border-ops-border bg-ops-bg" />
    );
  }

  const options: { value: Theme; label: string }[] = [
    { value: "light", label: "Light" },
    { value: "system", label: "System" },
    { value: "dark", label: "Dark" },
  ];

  return (
    <div
      className="flex items-center rounded-lg border border-ops-border bg-ops-bg p-0.5"
      role="group"
      aria-label="Theme"
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setTheme(opt.value)}
          className={`rounded-md px-2 py-1 text-[11px] font-medium transition-colors ${
            theme === opt.value
              ? "bg-ops-surface text-ops-text shadow-card-sm"
              : "text-ops-muted hover:text-ops-secondary"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

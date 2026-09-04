import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ops: {
          bg: "var(--bg)",
          surface: "var(--surface)",
          "surface-hover": "var(--surface-hover)",
          border: "var(--border)",
          "border-subtle": "var(--border-subtle)",
          text: "var(--text)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          accent: "var(--accent)",
          "accent-light": "var(--accent-light)",
          "accent-hover": "var(--accent-hover)",
          green: "var(--green)",
          "green-light": "var(--green-light)",
          amber: "var(--amber)",
          "amber-light": "var(--amber-light)",
          red: "var(--red)",
          "red-light": "var(--red-light)",
          cyan: "var(--cyan)",
          "cyan-light": "var(--cyan-light)",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "var(--shadow)",
        "card-md": "var(--shadow-md)",
        "card-sm": "var(--shadow-sm)",
      },
    },
  },
  plugins: [],
};

export default config;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: "#030508",
          900: "#070c14",
          800: "#0d1521",
          700: "#141e2e",
          600: "#1a2840",
          500: "#233352",
        },
        gold: {
          300: "#f5d98a",
          400: "#f0c84a",
          500: "#e8b320",
          600: "#c99510",
        },
        jade: {
          400: "#3dffc8",
          500: "#00e5a8",
          600: "#00c490",
        },
        crimson: {
          400: "#ff6b7a",
          500: "#ff4459",
          600: "#e83347",
        },
        slate: {
          750: "#1e2d45",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-mesh":
          "radial-gradient(at 40% 20%, hsla(220,100%,10%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(220,80%,8%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(220,100%,6%,1) 0px, transparent 50%)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "slide-right": "slideRight 0.3s ease-out",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideRight: {
          from: { opacity: "0", transform: "translateX(-12px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "-200% 0" },
          to: { backgroundPosition: "200% 0" },
        },
      },
      boxShadow: {
        gold: "0 0 30px rgba(232,179,32,0.15)",
        jade: "0 0 30px rgba(0,229,168,0.15)",
        card: "0 4px 24px rgba(0,0,0,0.4)",
        glow: "0 0 60px rgba(232,179,32,0.08)",
      },
    },
  },
  plugins: [],
};

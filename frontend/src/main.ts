import "./styles/app.css";
import { App } from "./app";
import { createAuth } from "./auth";

// Theme: saved preference, else the OS setting (GDD §5 / STYLE_GUIDE dark variant).
const savedTheme = localStorage.getItem("syntax.theme");
const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
document.documentElement.setAttribute("data-theme", savedTheme ?? (prefersDark ? "dark" : "light"));

// Register the service worker for the app-shell cache (near-instant repeat
// visits; offline shows the shell — the daily stack still needs the network).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      /* SW is a progressive enhancement; ignore failures */
    });
  });
}

const root = document.getElementById("app")!;
const app = new App(root, createAuth());
void app.boot();

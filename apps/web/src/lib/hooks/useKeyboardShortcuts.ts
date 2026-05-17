import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

function isInputFocused(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    (el as HTMLElement).isContentEditable
  );
}

export function useGlobalKeyboardShortcuts() {
  const navigate = useNavigate();
  const gPressedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // Ignore modified keys (except shift)
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "g" && !isInputFocused()) {
        gPressedRef.current = true;
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          gPressedRef.current = false;
        }, 500);
        return;
      }

      if (gPressedRef.current) {
        gPressedRef.current = false;
        if (timerRef.current) clearTimeout(timerRef.current);
        if (e.key === "d") {
          e.preventDefault();
          void navigate("/dashboard");
          return;
        }
        if (e.key === "p") {
          e.preventDefault();
          void navigate("/projects");
          return;
        }
      }

      if (isInputFocused()) return;

      if (e.key === "c") {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("shortcut:create"));
        return;
      }

      if (e.key === "/") {
        e.preventDefault();
        const el = document.querySelector<HTMLElement>("[data-shortcut-search]");
        el?.focus();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [navigate]);
}

export function useCreateShortcut(handler: () => void) {
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    function onShortcut() {
      handlerRef.current();
    }
    window.addEventListener("shortcut:create", onShortcut);
    return () => window.removeEventListener("shortcut:create", onShortcut);
  }, []);
}

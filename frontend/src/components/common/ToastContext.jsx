import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertTriangle, Info } from "lucide-react";
import styles from "./Toast.module.css";

const ToastContext = createContext(null);
const ICONS = { success: CheckCircle2, error: AlertTriangle, info: Info };

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, tone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className={styles.region} role="status" aria-live="polite">
        {toasts.map((t) => {
          const Icon = ICONS[t.tone] ?? Info;
          return (
            <div key={t.id} className={`${styles.toast} ${styles[t.tone]}`}>
              <Icon size={16} aria-hidden="true" />
              <span>{t.message}</span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

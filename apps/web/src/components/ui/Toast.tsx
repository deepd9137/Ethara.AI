import * as RadixToast from "@radix-ui/react-toast";
import { createContext, useId, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

type ToastVariant = "success" | "error" | "info";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  action?: ToastAction;
}

export interface ToastContextValue {
  toast: (opts: Omit<Toast, "id">) => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const ToastContext = createContext<ToastContextValue | null>(null);

const variantClasses: Record<ToastVariant, string> = {
  success: "border-success/30 bg-success/10 text-success",
  error: "border-danger/30 bg-danger/10 text-danger",
  info: "border-info/30 bg-info/10 text-info",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  function addToast(opts: Omit<Toast, "id">) {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { ...opts, id }]);
  }

  function removeToast(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <RadixToast.Provider swipeDirection="right">
        {children}

        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => removeToast(t.id)} />
        ))}

        <RadixToast.Viewport className="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const titleId = useId();
  return (
    <RadixToast.Root
      duration={toast.variant === "error" ? Infinity : 4_000}
      onOpenChange={(open) => !open && onDismiss()}
      aria-labelledby={titleId}
      className={cn(
        "rounded-lg border p-4 shadow-md",
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[swipe=end]:animate-out data-[state=closed]:fade-out-80",
        "data-[state=open]:slide-in-from-top-2",
        variantClasses[toast.variant],
      )}
    >
      <RadixToast.Title id={titleId} className="text-sm font-semibold">
        {toast.title}
      </RadixToast.Title>
      {toast.description && (
        <RadixToast.Description className="mt-1 text-xs opacity-80">
          {toast.description}
        </RadixToast.Description>
      )}
      {toast.action && (
        <RadixToast.Action
          altText={toast.action.label}
          onClick={toast.action.onClick}
          className="mt-2 rounded border border-current px-2 py-0.5 text-xs font-medium opacity-80 hover:opacity-100"
        >
          {toast.action.label}
        </RadixToast.Action>
      )}
      <RadixToast.Close
        className="absolute right-2 top-2 rounded p-0.5 opacity-60 hover:opacity-100"
        aria-label="Dismiss"
      >
        ×
      </RadixToast.Close>
    </RadixToast.Root>
  );
}

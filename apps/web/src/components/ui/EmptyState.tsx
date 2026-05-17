import { type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center gap-4 py-12 text-center", className)}>
      {icon && (
        <div className="text-muted text-4xl" aria-hidden="true">
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <p className="text-body font-semibold">{title}</p>
        {description && <p className="text-muted text-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}

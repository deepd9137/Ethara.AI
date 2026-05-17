import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils/cn";
import { useUiStore } from "@/store/ui";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Projects", to: "/projects" },
];

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  return (
    <aside
      aria-label="Main navigation"
      className={cn(
        "border-border bg-surface flex flex-col border-r transition-all duration-200",
        onClose ? "w-full" : "hidden md:flex",
        !onClose && (collapsed ? "md:w-14" : "md:w-56"),
      )}
    >
      <div className="border-border flex h-14 items-center justify-between border-b px-4">
        {(!collapsed || onClose) && (
          <span className="text-body text-sm font-semibold">Team Task Manager</span>
        )}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="text-muted hover:text-body rounded p-1"
          >
            ✕
          </button>
        )}
      </div>

      <nav className="flex flex-col gap-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted hover:bg-border hover:text-body",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

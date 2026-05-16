import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils/cn";
import { useUiStore } from "@/store/ui";

const navItems = [{ label: "Dashboard", to: "/dashboard" }];

export function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  return (
    <aside
      aria-label="Main navigation"
      className={cn(
        "border-border bg-surface hidden flex-col border-r transition-all duration-200 md:flex",
        collapsed ? "w-14" : "w-56",
      )}
    >
      <div className="border-border flex h-14 items-center border-b px-4">
        {!collapsed && <span className="text-body text-sm font-semibold">Team Task Manager</span>}
      </div>

      <nav className="flex flex-col gap-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
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

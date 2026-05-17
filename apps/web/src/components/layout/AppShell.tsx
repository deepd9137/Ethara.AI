import { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { MobileDrawer } from "./MobileDrawer";
import { useUiStore } from "@/store/ui";
import { useGlobalKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const mobileMenuOpen = useUiStore((s) => s.mobileMenuOpen);
  const setMobileMenuOpen = useUiStore((s) => s.setMobileMenuOpen);

  useGlobalKeyboardShortcuts();

  return (
    <div className="bg-bg flex min-h-screen">
      <Sidebar />
      <MobileDrawer open={mobileMenuOpen} onOpenChange={setMobileMenuOpen} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

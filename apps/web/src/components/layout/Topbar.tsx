import { useAuthStore } from "@/store/auth";
import { useUiStore } from "@/store/ui";
import { useLogout } from "@/features/auth/hooks";
import { Button } from "@/components/ui";

export function Topbar() {
  const user = useAuthStore((s) => s.user);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const logout = useLogout();

  return (
    <header className="border-border bg-bg flex h-14 items-center justify-between border-b px-4">
      <button
        type="button"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        className="text-muted hover:bg-surface hover:text-body hidden rounded p-1.5 md:flex"
      >
        ☰
      </button>

      <div className="ml-auto flex items-center gap-3">
        {user && <span className="text-muted hidden text-sm sm:block">{user.name}</span>}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => logout.mutate()}
          isLoading={logout.isPending}
        >
          Sign out
        </Button>
      </div>
    </header>
  );
}

import { LayoutDashboard, Brain, Film, FolderOpen, Settings } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "intelligence", label: "Intelligence", icon: Brain },
  { id: "studio", label: "Studio", icon: Film },
  { id: "assets", label: "Assets", icon: FolderOpen },
] as const;

interface SideNavProps {
  activeTab?: string;
}

export default function SideNav({ activeTab = "intelligence" }: SideNavProps) {
  return (
    <nav className="hidden lg:flex fixed left-0 top-0 bottom-0 w-20 bg-surface border-r border-outline-variant/20 flex-col items-center py-6 z-50">
      {/* Logo */}
      <span className="text-primary font-bold text-xl tracking-tighter mb-8">
        AS
      </span>

      {/* Navigation */}
      <div className="flex flex-col items-center gap-2 flex-1">
        {navItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              className={`relative flex flex-col items-center gap-1 w-full py-3 px-2 transition-colors ${
                isActive
                  ? "text-primary"
                  : "text-on-surface-variant/60 hover:text-primary hover:opacity-100"
              }`}
            >
              <Icon size={22} />
              <span className="text-label-sm">{label}</span>
              {isActive && (
                <span className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-primary rounded-l-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* Settings */}
      <button className="flex flex-col items-center gap-1 py-3 px-2 text-on-surface-variant/60 hover:text-primary transition-colors">
        <Settings size={22} />
        <span className="text-label-sm">Settings</span>
      </button>
    </nav>
  );
}

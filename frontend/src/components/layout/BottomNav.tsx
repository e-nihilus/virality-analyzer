import { LayoutDashboard, Brain, Film, Settings } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "intelligence", label: "Intelligence", icon: Brain },
  { id: "studio", label: "Studio", icon: Film },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

interface BottomNavProps {
  activeTab?: string;
}

export default function BottomNav({ activeTab = "intelligence" }: BottomNavProps) {
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 w-full z-50 rounded-t-xl bg-surface/90 backdrop-blur-xl border-t border-outline-variant/10">
      <div className="flex justify-around items-center h-20 px-4">
        {navItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              className={`flex flex-col items-center gap-1 py-2 px-3 transition-colors ${
                isActive
                  ? "text-primary -translate-y-0.5"
                  : "text-on-surface-variant/60 hover:text-primary/80"
              }`}
            >
              <Icon size={22} />
              <span className="text-label-sm">{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

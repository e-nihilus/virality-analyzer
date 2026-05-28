import { Brain, Bell, MoreVertical } from "lucide-react";

const desktopNavLinks = [
  { id: "overview", label: "Overview" },
  { id: "retention", label: "Retention" },
  { id: "viral-peaks", label: "Viral Peaks" },
  { id: "sentiment", label: "Sentiment" },
] as const;

const activeLink = "sentiment";

export default function TopAppBar() {
  return (
    <header className="fixed top-0 right-0 left-0 lg:left-20 z-40 h-16 bg-surface/80 backdrop-blur-xl border-b border-outline-variant/10">
      {/* Desktop */}
      <div className="hidden lg:flex items-center justify-between h-full px-6">
        <div className="flex items-center gap-8">
          <span className="text-on-surface font-bold text-lg tracking-tight">
            Aurea<span className="text-primary">Suite</span>
          </span>

          <nav className="flex items-center gap-1">
            {desktopNavLinks.map(({ id, label }) => {
              const isActive = id === activeLink;
              return (
                <button
                  key={id}
                  className={`px-3 py-4 text-body-md transition-colors ${
                    isActive
                      ? "text-primary font-bold border-b-2 border-primary"
                      : "text-on-surface-variant/60 hover:text-on-surface"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <button className="px-4 py-2 text-body-md text-on-surface-variant border border-outline-variant/30 rounded-md hover:bg-surface-container transition-colors">
            Share Project
          </button>
          <button className="px-4 py-2 text-body-md text-on-primary-container bg-primary-container hover:bg-inverse-primary rounded-md transition-colors font-medium">
            Export Clips
          </button>
          <button className="p-2 text-on-surface-variant/60 hover:text-on-surface transition-colors">
            <Bell size={20} />
          </button>
          <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center">
            <span className="text-label-sm text-on-surface-variant">AD</span>
          </div>
        </div>
      </div>

      {/* Mobile */}
      <div className="flex lg:hidden items-center justify-between h-full px-4">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-primary" />
          <span className="text-label-sm text-primary">NEURAL LENS</span>
        </div>
        <button className="p-2 text-on-surface-variant/60 hover:text-on-surface transition-colors">
          <MoreVertical size={20} />
        </button>
      </div>
    </header>
  );
}

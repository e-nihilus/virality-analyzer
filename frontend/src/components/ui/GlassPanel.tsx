import { forwardRef, type ReactNode } from "react";
import clsx from "clsx";

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  elevated?: boolean;
}

const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ children, className, elevated = false }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          elevated ? "glass-panel-elevated" : "glass-panel",
          "rounded-xl",
          className
        )}
      >
        {children}
      </div>
    );
  }
);

GlassPanel.displayName = "GlassPanel";

export default GlassPanel;

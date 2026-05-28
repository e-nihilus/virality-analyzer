import type { ReactNode } from "react";
import clsx from "clsx";

interface MetricCardProps {
  label: string;
  value: string;
  description?: string;
  icon: ReactNode;
  color?: string;
}

export default function MetricCard({
  label,
  value,
  description,
  icon,
  color = "text-secondary",
}: MetricCardProps) {
  return (
    <div className="bg-surface-container-high/40 p-5 rounded-xl border border-outline-variant/10">
      <span className="text-on-surface-variant text-label-sm block mb-1">
        {label}
      </span>
      <div className="flex items-center gap-2">
        <span className={clsx(color)}>{icon}</span>
        <span className={clsx("text-headline-md", color)}>{value}</span>
      </div>
      {description && (
        <p className="text-label-sm text-on-surface-variant mt-2">
          {description}
        </p>
      )}
    </div>
  );
}

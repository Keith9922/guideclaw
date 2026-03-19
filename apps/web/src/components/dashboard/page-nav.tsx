import type { DashboardView } from "./types";
import { viewLabels } from "./content";

type DashboardPageNavProps = {
  activeView: DashboardView;
  isRouting: boolean;
  onNavigate: (view: DashboardView) => void;
};

export function DashboardPageNav({
  activeView,
  isRouting,
  onNavigate,
}: DashboardPageNavProps) {
  return (
    <nav className="workspace-nav" aria-label="页面导航">
      {(Object.keys(viewLabels) as DashboardView[]).map((view) => {
        const meta = viewLabels[view];
        const Icon = meta.icon;
        return (
          <button
            key={view}
            className="workspace-nav-button"
            data-active={activeView === view}
            disabled={activeView === view || isRouting}
            onClick={() => onNavigate(view)}
            type="button"
          >
            <Icon size={16} />
            {meta.label}
          </button>
        );
      })}
    </nav>
  );
}

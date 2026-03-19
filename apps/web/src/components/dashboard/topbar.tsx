import { PanelRightClose, PanelRightOpen } from "lucide-react";

type DashboardTopbarProps = {
  title: string;
  description: string;
  badges: string[];
  showDetailToggle?: boolean;
  detailPanelOpen?: boolean;
  onToggleDetailPanel?: () => void;
};

export function DashboardTopbar({
  title,
  description,
  badges,
  showDetailToggle = false,
  detailPanelOpen = true,
  onToggleDetailPanel,
}: DashboardTopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-copy">
        <div className="brand-lockup">
          <div className="brand-logo-frame">
            <img className="brand-logo" src="/guideclaw-logo.png" alt="引路虾 Logo" />
          </div>
          <div className="brand-copy">
            <div className="topbar-kicker">GuideClaw · 学术龙虾工作台</div>
            <h1 className="topbar-title">{title}</h1>
            <p>{description}</p>
          </div>
        </div>
      </div>
      <div className="topbar-actions">
        {showDetailToggle ? (
          <button
            className="topbar-toggle"
            onClick={onToggleDetailPanel}
            type="button"
          >
            {detailPanelOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            {detailPanelOpen ? "收起辅助区" : "展开辅助区"}
          </button>
        ) : null}
        <div className="topbar-badges">
        {badges.map((badge, index) => (
          <span key={badge} className={`badge ${index === badges.length - 1 ? "solid" : "ghost"}`}>
            {badge}
          </span>
        ))}
        </div>
      </div>
    </header>
  );
}

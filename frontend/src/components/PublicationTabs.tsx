"use client";

import { useState } from "react";

export interface PublicationTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface PublicationTabsProps {
  tabs: PublicationTab[];
  defaultTab?: string;
}

export function PublicationTabs({ tabs, defaultTab }: PublicationTabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);
  const active = tabs.find((t) => t.id === activeTab);

  if (tabs.length === 0) return null;

  return (
    <div className="publication-tabs">
      <nav className="publication-tabs-nav" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.id === activeTab}
            className={`publication-tab${tab.id === activeTab ? " active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      {active && (
        <div className="publication-tab-content" role="tabpanel">
          {active.content}
        </div>
      )}
    </div>
  );
}

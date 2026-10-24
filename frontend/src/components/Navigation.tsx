import React from 'react';
import { LayoutDashboard, Target, GitCommit, Server } from 'lucide-react';

export type ScreenTab = 'overview' | 'accuracy' | 'history' | 'status';

interface NavigationProps {
  activeTab: ScreenTab;
  onTabChange: (tab: ScreenTab) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'overview' as ScreenTab, label: 'Trading Overview', icon: LayoutDashboard },
    { id: 'accuracy' as ScreenTab, label: 'Forecast Accuracy', icon: Target },
    { id: 'history' as ScreenTab, label: 'Forecast History & Vintages', icon: GitCommit },
    { id: 'status' as ScreenTab, label: 'Data Status & Cache', icon: Server },
  ];

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(13, 19, 33, 0.6)',
      padding: '0 1.5rem',
      gap: '0.25rem',
    }}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            className={`nav-tab ${isActive ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <Icon size={16} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};

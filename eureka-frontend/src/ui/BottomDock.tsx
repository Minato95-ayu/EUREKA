import type { Tab } from '../core/EurekaTypes'
import { tabs } from '../core/Constants'

interface BottomNavProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

export default function BottomDock({ activeTab, onTabChange }: BottomNavProps) {
  return (
    <nav className="bottom-nav">
      {tabs.map((tab: any) => (
        <button className={activeTab === tab.id ? 'active' : ''} key={tab.id} onClick={() => onTabChange(tab.id)}>
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  )
}

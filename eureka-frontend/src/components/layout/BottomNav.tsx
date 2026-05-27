import type { Tab } from '../../types'
import { tabs } from '../../data/constants'

interface BottomNavProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

export default function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  return (
    <nav className="bottom-nav">
      {tabs.map((tab) => (
        <button className={activeTab === tab.id ? 'active' : ''} key={tab.id} onClick={() => onTabChange(tab.id)}>
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  )
}

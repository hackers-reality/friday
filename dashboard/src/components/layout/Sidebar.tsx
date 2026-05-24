import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useSystemStore } from '../../stores/useSystemStore'
import {
  MessageSquare, Mic, ClipboardList, Bot, Search, Globe, Eye,
  Brain, Youtube, Package, BarChart3, Monitor, Calendar,
  Terminal, Shield, ScrollText, Settings, ChevronLeft, ChevronRight,
} from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { icon: MessageSquare, label: 'Chat', path: '/' },
  { icon: Mic, label: 'Voice', path: '/voice' },
  { icon: ClipboardList, label: 'Tasks', path: '/tasks' },
  { icon: Bot, label: 'Agents', path: '/agents' },
  { icon: Search, label: 'OSINT', path: '/osint' },
  { icon: Globe, label: 'Browser', path: '/browser' },
  { icon: Eye, label: 'Vision', path: '/vision' },
  { icon: Brain, label: 'Memory', path: '/memory' },
  { icon: Youtube, label: 'YouTube', path: '/youtube' },
  { icon: Package, label: 'Takeout', path: '/takeout' },
  { icon: BarChart3, label: 'Analytics', path: '/analytics' },
  { icon: Monitor, label: 'Devices', path: '/devices' },
  { icon: Calendar, label: 'Scheduler', path: '/scheduler' },
  { icon: Terminal, label: 'PyRunner', path: '/pyrunner' },
  { icon: Shield, label: 'Security', path: '/security' },
  { icon: ScrollText, label: 'Logs', path: '/logs' },
  { icon: Settings, label: 'Settings', path: '/settings' },
]

export function Sidebar() {
  const collapsed = useSystemStore((s) => s.sidebarCollapsed)
  const toggle = useSystemStore((s) => s.toggleSidebar)

  return (
    <motion.aside
      className="h-full bg-friday-sidebar border-r border-border-cyan flex flex-col overflow-hidden select-none"
      animate={{ width: collapsed ? 56 : 200 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Collapse toggle */}
      <button
        onClick={toggle}
        className="flex items-center justify-center h-10 mt-2 mb-1 mx-auto text-text-dim hover:text-neon-cyan transition-colors"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-1 space-y-0.5">
        {NAV_ITEMS.map(({ icon: Icon, label, path }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 mx-1.5 rounded-lg text-sm transition-all duration-150 group',
                isActive
                  ? 'bg-friday-card text-neon-cyan border-l-[3px] border-neon-cyan'
                  : 'text-text-dim hover:text-neon-cyan hover:bg-friday-card/50 border-l-[3px] border-transparent',
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="truncate"
              >
                {label}
              </motion.span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom branding */}
      {!collapsed && (
        <div className="p-3 border-t border-border-cyan">
          <div className="text-[10px] text-text-muted text-center font-mono">FRIDAY v2.0</div>
        </div>
      )}
    </motion.aside>
  )
}

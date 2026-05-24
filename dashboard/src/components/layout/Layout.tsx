import { useLocation, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare } from 'lucide-react'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { ChatPanel } from '../chat/ChatPanel'
import { useSystemStore } from '../../stores/useSystemStore'
import { useState } from 'react'

const FULL_WIDTH_ROUTES = ['/security', '/logs', '/settings']

export function Layout() {
  const location = useLocation()
  const sidebarCollapsed = useSystemStore((s) => s.sidebarCollapsed)
  const isFullWidth = FULL_WIDTH_ROUTES.includes(location.pathname)
  const [chatHidden, setChatHidden] = useState(false)

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        {isFullWidth ? (
          /* Full-width page layout */
          <div className="flex-1 flex overflow-hidden">
            <main className="flex-1 overflow-y-auto">
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.15 }}
                  className="h-full"
                >
                  <Outlet />
                </motion.div>
              </AnimatePresence>
            </main>
            {!chatHidden && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 380, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="border-l border-border-cyan overflow-hidden"
              >
                <ChatPanel />
              </motion.div>
            )}
            {chatHidden && (
              <button
                onClick={() => setChatHidden(false)}
                className="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full bg-neon-cyan text-friday-bg flex items-center justify-center shadow-lg shadow-neon-cyan/20 hover:scale-105 transition-transform"
                title="Open Chat"
              >
                <MessageSquare size={20} />
              </button>
            )}
          </div>
        ) : (
          /* Standard 3-column layout */
          <div className="flex-1 flex overflow-hidden">
            {/* Center: Chat */}
            <div
              className="flex-1 border-r border-border-cyan overflow-hidden"
              style={{ minWidth: 320 }}
            >
              <ChatPanel />
            </div>
            {/* Right: Page content */}
            <motion.div
              className="overflow-y-auto overflow-x-hidden"
              style={{ width: sidebarCollapsed ? 420 : 380 }}
              layout
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -12 }}
                  transition={{ duration: 0.15 }}
                  className="p-4 min-h-full"
                >
                  <Outlet />
                </motion.div>
              </AnimatePresence>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}

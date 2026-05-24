import { useLocation, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Cpu, Terminal, Loader2 } from 'lucide-react'
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
  const runningAgents = useSystemStore((s) => s.agents.filter((a) => a.status === 'running'))
  const logs = useSystemStore((s) => s.logs)

  const getAgentLogs = (agentName: string) => {
    return logs
      .filter((l) => 
        l.message.toLowerCase().includes(agentName.toLowerCase()) || 
        (l.module && l.module.toLowerCase().includes(agentName.toLowerCase()))
      )
      .slice(-3)
  }

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

      {/* Floating Active Agent HUD */}
      <AnimatePresence>
        {runningAgents.map((agent, index) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed bottom-6 z-50 w-80 bg-friday-bg/95 border border-neon-cyan/50 rounded-lg p-4 shadow-lg shadow-neon-cyan/15 backdrop-blur-md flex flex-col gap-3 font-mono"
            style={{
              right: chatHidden ? 24 + index * 340 : 404 + index * 340,
              boxShadow: '0 0 15px rgba(0, 242, 254, 0.15)',
              background: 'radial-gradient(circle at top left, rgba(0, 242, 254, 0.05), transparent 70%), #0A1118',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-neon-cyan/20 pb-2">
              <div className="flex items-center gap-2">
                <Loader2 size={14} className="text-neon-cyan animate-spin" />
                <span className="text-[10px] uppercase tracking-widest text-neon-cyan font-bold">
                  Friday Sublink
                </span>
              </div>
              <span className="text-[9px] text-neon-cyan/70 bg-neon-cyan/10 px-2 py-0.5 rounded border border-neon-cyan/20 animate-pulse">
                ACTIVE
              </span>
            </div>

            {/* Content */}
            <div className="flex flex-col gap-1">
              <span className="text-xs font-bold text-gray-100">{agent.display_name}</span>
              <span className="text-[9px] text-gray-400">
                Targeting: {agent.model}
              </span>
              <div className="mt-1 p-2 bg-black/40 border border-neon-cyan/10 rounded flex flex-col gap-1">
                <span className="text-[9px] text-neon-cyan/80 flex items-center gap-1 font-bold">
                  <Cpu size={10} />
                  CURRENT INSTRUCTION:
                </span>
                <span className="text-[11px] text-gray-200 line-clamp-2">
                  {agent.current_task || 'Awaiting dispatch directives...'}
                </span>
                {agent.current_action && (
                  <span className="text-[9px] text-neon-cyan/80 mt-1 border-t border-neon-cyan/5 pt-1 italic">
                    &gt; {agent.current_action}
                  </span>
                )}
                {typeof agent.progress === 'number' && agent.progress > 0 && (
                  <div className="mt-1 flex flex-col gap-0.5">
                    <div className="flex justify-between text-[8px] text-neon-cyan/80 font-bold">
                      <span>PROGRESS</span>
                      <span>{agent.progress}%</span>
                    </div>
                    <div className="h-1 bg-black/60 rounded overflow-hidden">
                      <div
                        className="h-full bg-neon-cyan transition-all duration-300"
                        style={{ width: `${agent.progress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Futuristic terminal logs */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-[9px] text-neon-cyan/50">
                <Terminal size={9} />
                <span>NEURAL STREAM</span>
              </div>
              <div className="text-[9px] text-gray-400 bg-black/50 p-2 rounded border border-neon-cyan/5 font-mono h-16 overflow-y-auto flex flex-col gap-1">
                {getAgentLogs(agent.name).length > 0 ? (
                  getAgentLogs(agent.name).map((log, i) => (
                    <div key={i} className="text-[8px] leading-tight text-gray-300">
                      <span className="text-neon-cyan/50">&gt;</span> {log.message}
                    </div>
                  ))
                ) : (
                  <div className="text-[8px] italic text-gray-500">
                    &gt; connection secure. listening to neural link...
                  </div>
                )}
              </div>
            </div>

            {/* Pulse bar */}
            <div className="h-0.5 bg-black/50 rounded overflow-hidden relative">
              <motion.div
                className="absolute inset-0 bg-neon-cyan"
                animate={{
                  x: ['-100%', '100%'],
                }}
                transition={{
                  repeat: Infinity,
                  duration: 1.5,
                  ease: 'linear',
                }}
              />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

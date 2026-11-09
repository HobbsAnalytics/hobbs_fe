import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Clock,
  DollarSign,
  FileText,
  LayoutDashboard,
  ShieldCheck,
} from 'lucide-react';
import { useAppStore } from '../../stores/appStore';
import { useComplianceSummary } from '../../hooks/useProjectData';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string; // undefined: page not built yet -> disabled with a "Soon" tag (no fake route)
  match?: (pathname: string) => boolean;
}

const navItems: NavItem[] = [
  { id: 'copilot', label: 'AI Co-Pilot', icon: <Bot size={20} />, path: '/', match: (p) => p === '/' },
  { id: 'dashboards', label: 'Dashboards', icon: <LayoutDashboard size={20} /> },
  {
    id: 'compliance',
    label: 'Doc Compliance',
    icon: <FileText size={20} />,
    path: '/compliance',
    match: (p) => p.startsWith('/compliance') || p.startsWith('/drawings/'),
  },
  { id: 'schedule', label: 'Schedule & Risk', icon: <Clock size={20} /> },
  { id: 'cost', label: 'Cost & Budget', icon: <DollarSign size={20} /> },
  { id: 'safety', label: 'Safety & Quality', icon: <ShieldCheck size={20} /> },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const summary = useComplianceSummary();
  // Badge = drawings that failed review this week, straight from /api/compliance/summary. No data, no badge.
  const failed = summary.data?.failed;

  return (
    <motion.aside
      className="fixed left-0 top-0 h-screen sidebar-gradient z-40 flex flex-col border-r border-slate-700/50"
      initial={false}
      animate={{ width: sidebarCollapsed ? 72 : 256 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-700/50">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
          BR
        </div>
        {!sidebarCollapsed && (
          <div className="overflow-hidden whitespace-nowrap leading-tight">
            <h1 className="text-sm font-bold text-white tracking-wide">Blue Ridge LNG</h1>
            <p className="text-[10px] text-slate-400 font-medium">Project Intelligence</p>
          </div>
        )}
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto" aria-label="Main">
        {navItems.map((item) => {
          const enabled = !!item.path;
          const active = enabled && (item.match ? item.match(pathname) : pathname === item.path);
          const badge = item.id === 'compliance' && typeof failed === 'number' ? failed : undefined;
          return (
            <div key={item.id} className="relative">
              {active && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 bg-slate-700/60 rounded-lg"
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}
              <button
                type="button"
                onClick={enabled ? () => navigate(item.path!) : undefined}
                disabled={!enabled}
                aria-disabled={!enabled}
                aria-current={active ? 'page' : undefined}
                title={!enabled ? `${item.label}: coming soon` : sidebarCollapsed ? item.label : undefined}
                className={`nav-item w-full relative z-10 ${
                  !enabled
                    ? 'text-slate-500 cursor-not-allowed'
                    : active
                      ? 'text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                }`}
              >
                <span className="flex-shrink-0">{item.icon}</span>
                {!sidebarCollapsed && <span className="overflow-hidden whitespace-nowrap flex-1 text-left">{item.label}</span>}
                {!enabled && !sidebarCollapsed && (
                  <span className="ml-auto text-[10px] font-semibold uppercase tracking-wide text-slate-400 bg-slate-700/50 border border-slate-600/50 px-1.5 py-0.5 rounded">
                    Soon
                  </span>
                )}
                {badge !== undefined && !sidebarCollapsed && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    data-testid="nav-badge"
                    title={`${badge} drawings failed review this week`}
                    className="ml-auto bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-2 py-0.5 rounded-full"
                  >
                    {badge}
                  </motion.span>
                )}
                {badge !== undefined && sidebarCollapsed && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-emerald-400 rounded-full" />
                )}
              </button>
            </div>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-slate-700/50 flex items-center gap-2 text-xs text-slate-400">
        <span className="relative flex h-2 w-2 flex-shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
        {!sidebarCollapsed && <span>Synthetic demo data</span>}
      </div>
      <div className="p-2 border-t border-slate-700/50">
        <button
          type="button"
          onClick={toggleSidebar}
          className="nav-item w-full text-slate-400 hover:text-white hover:bg-slate-700/30 justify-center"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-xs">
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;

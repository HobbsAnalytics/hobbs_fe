import React from 'react';
import { NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom';
import {
  Activity,
  Bot,
  FileCheck2,
  FileText,
  CalendarClock,
  ShieldAlert,
  LayoutDashboard,
} from 'lucide-react';

// Scaffold shell only. Task 21 replaces Sidebar/TopBar with the full components,
// Task 22 the chat, Task 23 the PDF viewer.

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Co-Pilot', icon: Bot, to: '/' },
  { label: 'Compliance', icon: FileCheck2, to: '/compliance' },
  { label: 'Drawings', icon: FileText, to: '/drawings/DWG-001' },
  { label: 'Schedule', icon: CalendarClock, to: '/schedule' },
  { label: 'Risk & Safety', icon: ShieldAlert, to: '/risk' },
];

const Sidebar: React.FC = () => (
  <aside className="fixed left-0 top-0 h-screen w-64 sidebar-gradient z-40 flex flex-col border-r border-slate-700/50">
    <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-700/50">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
        BR
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold text-white">Blue Ridge LNG</div>
        <div className="text-[11px] text-slate-400">Project Intelligence</div>
      </div>
    </div>
    <nav className="flex-1 px-3 py-4 space-y-1">
      {navItems.map(({ label, icon: Icon, to }) => (
        <NavLink
          key={label}
          to={to}
          className="nav-item text-slate-300 hover:bg-white/10 hover:text-white"
        >
          <Icon size={18} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
    <div className="px-4 py-3 border-t border-slate-700/50 flex items-center gap-2 text-xs text-slate-400">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      Synthetic demo data
    </div>
  </aside>
);

const crumbs: Record<string, string> = {
  '/': 'Co-Pilot',
  '/compliance': 'Compliance',
};

const TopBar: React.FC = () => {
  const { pathname } = useLocation();
  const current = pathname.startsWith('/drawings/') ? 'Drawings' : crumbs[pathname] ?? 'Page';
  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center px-6 gap-2 text-sm">
      <Activity size={16} className="text-emerald-600" />
      <span className="text-slate-500">Blue Ridge LNG</span>
      <span className="text-slate-300">/</span>
      <span className="font-medium text-slate-900" data-testid="breadcrumb">{current}</span>
    </header>
  );
};

const Placeholder: React.FC<{ id: string; title: string; children?: React.ReactNode }> = ({
  id,
  title,
  children,
}) => (
  <div className="page-container" data-testid={id}>
    <h1 className="section-header">{title}</h1>
    <div className="metric-card text-slate-500 text-sm">{children ?? 'Coming soon.'}</div>
  </div>
);

const DrawingPlaceholder: React.FC = () => {
  const { id } = useParams();
  return (
    <Placeholder id="page-drawing" title="Drawing">
      Drawing {id}
    </Placeholder>
  );
};

const App: React.FC = () => (
  <div className="min-h-screen bg-slate-50">
    <Sidebar />
    <div className="ml-64 flex flex-col min-h-screen">
      <TopBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Placeholder id="page-copilot" title="Project Co-Pilot" />} />
          <Route path="/compliance" element={<Placeholder id="page-compliance" title="Compliance" />} />
          <Route path="/drawings/:id" element={<DrawingPlaceholder />} />
          <Route path="*" element={<Placeholder id="page-notfound" title="Not found" />} />
        </Routes>
      </main>
    </div>
  </div>
);

export default App;

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Bell, Building2, Check, ChevronDown, Search } from 'lucide-react';
import { useAppStore } from '../../stores/appStore';
import { useWhoami } from '../../hooks/useWhoami';
import { useComplianceSummary, useScheduleOverdue } from '../../hooks/useProjectData';
import { DRAWING_ID_RE } from '../../lib/api';
import { AUTH_MODE_LABEL, initialsFromEmail } from '../../lib/format';

const PROJECT_NAME = 'Blue Ridge LNG Terminal — Phase 2';

function pageName(pathname: string): string {
  if (pathname === '/') return 'AI Co-Pilot';
  if (pathname.startsWith('/compliance')) return 'Doc Compliance';
  if (pathname.startsWith('/drawings/')) return 'Drawing';
  return 'Not found';
}

interface Alert {
  id: string;
  title: string;
  tone: 'error' | 'warning';
  to: string;
}

const TopBar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const setPendingPrompt = useAppStore((s) => s.setPendingPrompt);
  const whoami = useWhoami();
  const overdue = useScheduleOverdue();
  const summary = useComplianceSummary();

  const [projectOpen, setProjectOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [query, setQuery] = useState('');
  const projectRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (projectRef.current && !projectRef.current.contains(t)) setProjectOpen(false);
      if (notifRef.current && !notifRef.current.contains(t)) setNotifOpen(false);
      if (userRef.current && !userRef.current.contains(t)) setUserOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  // Bell items are derived from API data only (no seeded notifications).
  const alerts = useMemo<Alert[]>(() => {
    const out: Alert[] = [];
    const o = overdue.data;
    if (o && o.late > 0) out.push({ id: 'late', title: `${o.late} milestone${o.late === 1 ? ' is' : 's are'} late`, tone: 'error', to: '/' });
    if (o && o.due_today > 0) out.push({ id: 'due', title: `${o.due_today} milestone${o.due_today === 1 ? '' : 's'} due today`, tone: 'warning', to: '/' });
    const s = summary.data;
    if (s && s.failed > 0) out.push({ id: 'failed', title: `${s.failed} drawings failed review this week`, tone: 'error', to: '/compliance' });
    return out;
  }, [overdue.data, summary.data]);

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    const id = q.toUpperCase();
    if (DRAWING_ID_RE.test(id)) navigate(`/drawings/${id}`);
    else {
      setPendingPrompt(q);
      navigate('/');
    }
    setQuery('');
  };

  const email = whoami.data?.email ?? null;
  const mode = whoami.data?.auth_mode;

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-30 flex-shrink-0">
      <div className="flex items-center gap-2" data-testid="breadcrumb">
        <span className="text-sm text-slate-400">Project Intelligence</span>
        <span className="text-slate-300">/</span>
        <span className="text-sm font-semibold text-slate-900">{pageName(location.pathname)}</span>
      </div>

      <div className="flex items-center gap-4">
        <form onSubmit={onSearch} className="relative" role="search">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            aria-label="Search a drawing ID or ask a question"
            placeholder="Drawing ID or a question…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm w-64
              focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500
              placeholder:text-slate-400 transition-all"
          />
        </form>

        <div className="relative" ref={projectRef}>
          <button
            type="button"
            onClick={() => setProjectOpen(!projectOpen)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm hover:bg-slate-100 transition-colors"
          >
            <Building2 size={16} className="text-slate-500" />
            <span className="text-slate-700 max-w-[180px] truncate">Phase 2 — Terminal</span>
            <ChevronDown size={14} className={`text-slate-400 transition-transform ${projectOpen ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence>
            {projectOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 w-72 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50"
              >
                <div className="px-4 py-2 text-[11px] uppercase tracking-wide text-slate-400 font-semibold border-b border-slate-100">
                  Projects you can access
                </div>
                <button
                  type="button"
                  onClick={() => setProjectOpen(false)}
                  className="w-full text-left px-4 py-2.5 text-sm bg-emerald-50 text-emerald-700 font-medium flex items-center justify-between"
                >
                  {PROJECT_NAME}
                  <Check size={14} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
            aria-label="Alerts"
          >
            <Bell size={20} className="text-slate-600" />
            {alerts.length > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                data-testid="bell-count"
                className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center"
              >
                {alerts.length}
              </motion.span>
            )}
          </button>
          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 w-80 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50"
              >
                <div className="px-4 py-3 border-b border-slate-100">
                  <h3 className="text-sm font-semibold text-slate-900">Alerts</h3>
                  <p className="text-[11px] text-slate-400">From the schedule and compliance data</p>
                </div>
                {alerts.length === 0 ? (
                  <p className="px-4 py-4 text-sm text-slate-500">
                    {overdue.isLoading || summary.isLoading ? 'Loading…' : overdue.isError || summary.isError ? "Alerts couldn't be loaded." : 'Nothing needs attention.'}
                  </p>
                ) : (
                  alerts.map((a) => (
                    <button
                      type="button"
                      key={a.id}
                      onClick={() => {
                        setNotifOpen(false);
                        navigate(a.to);
                      }}
                      className="w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 flex items-start gap-3"
                    >
                      <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${a.tone === 'error' ? 'bg-red-500' : 'bg-amber-500'}`} />
                      <span className="text-sm text-slate-800">{a.title}</span>
                    </button>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative" ref={userRef}>
          <button
            type="button"
            onClick={() => setUserOpen(!userOpen)}
            className="flex items-center gap-2 hover:bg-slate-100 rounded-lg p-1.5 transition-colors"
            aria-label="Signed-in user"
          >
            <div
              className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center"
              data-testid="avatar"
              title={email ?? undefined}
            >
              <span className="text-[11px] font-bold text-white">{whoami.isLoading ? '' : initialsFromEmail(email)}</span>
            </div>
            {mode && (
              <span
                data-testid="avatar-mode"
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${mode === 'OBO' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-blue-50 text-blue-700 border-blue-200'}`}
              >
                {mode}
              </span>
            )}
            <ChevronDown size={14} className="text-slate-400" />
          </button>
          <AnimatePresence>
            {userOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 w-72 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50"
              >
                <div className="px-4 py-3">
                  {whoami.isError ? (
                    <p className="text-sm text-red-600">Couldn't read the signed-in identity.</p>
                  ) : (
                    <>
                      <p className="text-sm font-semibold text-slate-900 truncate">{email ?? 'No forwarded user'}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {mode === 'OBO'
                          ? `Signed in as you. Genie runs ${AUTH_MODE_LABEL.OBO}; tiles read through the app's service principal.`
                          : mode === 'SP'
                            ? `No user token forwarded: requests run ${AUTH_MODE_LABEL.SP}.`
                            : 'Loading identity…'}
                      </p>
                    </>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
};

export default TopBar;

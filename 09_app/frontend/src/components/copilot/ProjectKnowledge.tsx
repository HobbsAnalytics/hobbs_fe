import React from 'react';
import { Bot, Database, FileText, Target } from 'lucide-react';

// Static labels for the data sources behind the Co-Pilot. No counts: any count would have to come from the API.
const SOURCES = [
  { icon: <FileText size={14} />, title: 'Drawings Volume', sub: '/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings' },
  { icon: <Database size={14} />, title: 'Project gold schema', sub: 'mfg_mc_se_sa.bluerridge_gold_pm' },
  { icon: <Target size={14} />, title: 'Vector Search index', sub: 'code_excerpts_vs · ASME, OSHA, IBC excerpts' },
  { icon: <Bot size={14} />, title: 'Genie space', sub: 'space 01f1db9edffa1a298195db2806ce45e3' },
];

const ProjectKnowledge: React.FC = () => (
  <div className="rail-card">
    <div className="rail-title">Project Knowledge</div>
    {SOURCES.map((s) => (
      <div key={s.title} className="flex items-center gap-2.5 py-2 border-b border-slate-100 last:border-b-0 text-xs">
        <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center text-slate-500 flex-shrink-0">{s.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="text-slate-800 font-medium text-xs">{s.title}</div>
          <div className="text-slate-500 text-[11px] mt-0.5 font-mono truncate" title={s.sub}>
            {s.sub}
          </div>
        </div>
      </div>
    ))}
    <p className="mt-2 text-[10px] text-slate-400 leading-snug">
      Chat answers come from Genie, run as you. Tiles and KPIs are read by the app's service principal.
    </p>
  </div>
);

export default ProjectKnowledge;

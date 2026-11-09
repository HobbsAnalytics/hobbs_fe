import React, { Suspense, lazy } from 'react';
import { Link, Route, Routes, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import PageTransition from './components/layout/PageTransition';
import CopilotPage from './components/copilot/CopilotPage';
import CompliancePage from './components/compliance/CompliancePage';
import { ChatProvider } from './components/copilot/ChatContext';
import EmptyState from './components/shared/EmptyState';
import LoadingSkeleton from './components/shared/LoadingSkeleton';
import { useAppStore } from './stores/appStore';

// pdf.js is large: the drawing viewer is its own chunk, loaded on first visit to /drawings/:id.
const DrawingPage = lazy(() => import('./components/drawings/DrawingPage'));

const NotFound: React.FC = () => (
  <PageTransition>
    <div className="page-container" data-testid="page-notfound">
      <div className="bg-white rounded-xl border border-slate-200">
        <EmptyState title="This page doesn't exist" description="Head back to the Co-Pilot to ask a question." />
        <div className="text-center pb-6 -mt-4">
          <Link to="/" className="text-xs font-medium text-emerald-700 hover:text-emerald-800">
            Go to AI Co-Pilot →
          </Link>
        </div>
      </div>
    </div>
  </PageTransition>
);

const App: React.FC = () => {
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  return (
    <ChatProvider>
      <div className="min-h-screen bg-slate-50">
        <Sidebar />
        <div className="flex flex-col min-h-screen transition-[margin] duration-300" style={{ marginLeft: collapsed ? 72 : 256 }}>
          <TopBar />
          <main className="flex-1">
            <AnimatePresence mode="wait">
              <Routes location={location} key={location.pathname}>
                <Route path="/" element={<CopilotPage />} />
                <Route path="/compliance" element={<CompliancePage />} />
                <Route
                  path="/drawings/:id"
                  element={
                    <Suspense
                      fallback={
                        <div className="page-container">
                          <LoadingSkeleton type="card" count={2} />
                        </div>
                      }
                    >
                      <DrawingPage />
                    </Suspense>
                  }
                />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </ChatProvider>
  );
};

export default App;

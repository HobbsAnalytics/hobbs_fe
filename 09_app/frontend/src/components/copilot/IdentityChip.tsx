import React from 'react';
import { useWhoami } from '../../hooks/useWhoami';

/**
 * Who the chat runs as, from GET /api/whoami. OBO (a user token was forwarded): Genie runs as the signed-in user, so
 * their Unity Catalog permissions apply. SP: no user token reached the app, so it is acting as itself.
 */
const IdentityChip: React.FC = () => {
  const { data, isLoading, isError } = useWhoami();

  let dot = 'bg-slate-300';
  let text: React.ReactNode = 'Checking identity…';
  let title = 'Reading the signed-in identity from /api/whoami';
  if (isError) {
    dot = 'bg-red-500';
    text = 'Identity unavailable';
    title = "Couldn't read /api/whoami";
  } else if (data) {
    const who = data.email ?? data.user_name ?? 'No forwarded user';
    if (data.auth_mode === 'OBO') {
      dot = 'bg-emerald-500';
      text = (
        <>
          <span className="font-medium text-slate-700">{who}</span>
          <span className="text-slate-400"> · </span>Genie runs as you (on-behalf-of)
        </>
      );
      title = 'Your user token is forwarded, so Genie queries run with your own Unity Catalog permissions.';
    } else {
      dot = 'bg-blue-500';
      text = (
        <>
          <span className="font-medium text-slate-700">{who}</span>
          <span className="text-slate-400"> · </span>Runs as the app (service principal)
        </>
      );
      title = 'No user token was forwarded to the app, so requests run as the app service principal.';
    }
  } else if (!isLoading) {
    text = 'Identity unavailable';
  }

  return (
    <div
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] text-slate-600 max-w-full"
      data-testid="identity-chip"
      title={title}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
      <span className="truncate">{text}</span>
    </div>
  );
};

export default IdentityChip;

import React from 'react';
import ReactMarkdown from 'react-markdown';

// react-markdown with raw HTML skipped (no rehype-raw): model text can never inject markup. Links open in a new tab;
// react-markdown's default urlTransform already drops javascript: and other unsafe schemes.
const Markdown: React.FC<{ children: string; className?: string }> = ({ children, className = '' }) => (
  <div className={`markdown-body ${className}`}>
    <ReactMarkdown
      skipHtml
      components={{
        a: ({ node: _n, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
      }}
    >
      {children}
    </ReactMarkdown>
  </div>
);

export default Markdown;

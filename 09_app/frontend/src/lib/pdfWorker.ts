// pdf.js worker for react-pdf 9.2.1 (pdfjs-dist 4.8.69, pinned to the exact version react-pdf depends on).
// The `?url` import makes Vite emit the worker as a hashed asset in dist/assets and return its URL, which works in
// `vite dev`, `vite build` and the FastAPI-served SPA alike (no CDN, no bare-specifier `new URL()` resolution).
import { pdfjs } from 'react-pdf';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export { pdfjs };

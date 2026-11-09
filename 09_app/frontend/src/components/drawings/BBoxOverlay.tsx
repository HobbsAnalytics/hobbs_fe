import React, { forwardRef } from 'react';

/**
 * One finding's highlight over a rendered PDF page.
 *
 * Convention (project-wide, see 09_app/outputs/chat_selftest.md "About bbox"): bbox = normalized [x, y, w, h], 0..1,
 * top-left origin. It is multiplied by the rendered page's pixel width/height. `units="px"` accepts a box already in
 * page pixels (used by the plan's test).
 *
 * The box is clamped to the page. It is labelled "approximate location" when any of these hold:
 *  - it was out of bounds (clamping changed it),
 *  - it covers more than 25% of the page area,
 *  - its bbox_source is not 'ground_truth' (parse_element boxes, whole-page boxes, unknown source).
 */
export interface PageSize {
  w: number;
  h: number;
}

export interface OverlayBox {
  left: number;
  top: number;
  width: number;
  height: number;
  outOfBounds: boolean;
  areaFraction: number;
}

const EPS = 1e-6;
const MIN_PX = 4; // keep a clamped sliver visible

export function computeOverlayBox(page: PageSize, bbox: readonly number[], units: 'normalized' | 'px' = 'normalized'): OverlayBox {
  const W = Math.max(0, page.w);
  const H = Math.max(0, page.h);
  const [x0, y0, w0, h0] = bbox.map((v) => (Number.isFinite(v) ? v : 0));
  const sx = units === 'px' ? 1 : W;
  const sy = units === 'px' ? 1 : H;
  let x1 = x0 * sx;
  let y1 = y0 * sy;
  let x2 = x1 + Math.max(0, w0) * sx;
  let y2 = y1 + Math.max(0, h0) * sy;
  const outOfBounds = x1 < -EPS || y1 < -EPS || x2 > W + EPS || y2 > H + EPS || w0 < 0 || h0 < 0;

  const clamp = (v: number, max: number) => Math.min(Math.max(v, 0), max);
  x1 = clamp(x1, W);
  y1 = clamp(y1, H);
  x2 = clamp(x2, W);
  y2 = clamp(y2, H);
  // A box entirely off-page collapses to an edge: show a minimum-size marker inside the page at that edge.
  if (x2 - x1 < MIN_PX) {
    if (x1 + MIN_PX > W) x1 = Math.max(0, W - MIN_PX);
    x2 = Math.min(W, x1 + MIN_PX);
  }
  if (y2 - y1 < MIN_PX) {
    if (y1 + MIN_PX > H) y1 = Math.max(0, H - MIN_PX);
    y2 = Math.min(H, y1 + MIN_PX);
  }
  const r = (v: number) => Math.round(v * 100) / 100;
  const width = r(x2 - x1);
  const height = r(y2 - y1);
  const areaFraction = W > 0 && H > 0 ? (width * height) / (W * H) : 0;
  return { left: r(x1), top: r(y1), width, height, outOfBounds, areaFraction };
}

export function isApproximate(box: OverlayBox, source: string | null | undefined): boolean {
  return box.outOfBounds || box.areaFraction > 0.25 || source !== 'ground_truth';
}

interface BBoxOverlayProps {
  page: PageSize;
  bbox: readonly number[];
  units?: 'normalized' | 'px';
  source?: string | null;
  selected?: boolean;
  label?: string;
  onClick?: () => void;
}

const BBoxOverlay = forwardRef<HTMLDivElement, BBoxOverlayProps>(
  ({ page, bbox, units = 'normalized', source, selected = false, label, onClick }, ref) => {
    const box = computeOverlayBox(page, bbox, units);
    const approx = isApproximate(box, source);
    const whole = box.areaFraction > 0.95;
    const color = selected ? 'border-red-500 bg-red-500/15' : 'border-amber-500 bg-amber-400/10';

    return (
      <div
        ref={ref}
        data-testid="bbox-rect"
        data-approximate={approx}
        onClick={onClick}
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
        aria-label={label ? `${label}${approx ? ' (approximate location)' : ''}` : undefined}
        className={`absolute border-2 rounded-sm transition-colors ${approx ? 'border-dashed' : ''} ${color} ${onClick ? 'cursor-pointer' : ''} ${
          selected ? 'z-20 shadow-[0_0_0_3px_rgba(239,68,68,0.15)]' : 'z-10'
        }`}
        style={{ left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px`, height: `${box.height}px` }}
      >
        {(approx || label) && (
          <span
            className={`absolute ${whole || box.top < 20 ? 'top-1 left-1' : '-top-5 left-0'} whitespace-nowrap text-[10px] font-medium px-1.5 py-0.5 rounded ${
              selected ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
            }`}
          >
            {label}
            {label && approx ? ' · ' : ''}
            {approx ? 'approximate location' : ''}
          </span>
        )}
      </div>
    );
  },
);
BBoxOverlay.displayName = 'BBoxOverlay';

export default BBoxOverlay;

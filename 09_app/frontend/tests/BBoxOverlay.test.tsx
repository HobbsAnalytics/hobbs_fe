import { render } from '@testing-library/react';
import { describe, expect, it, test } from 'vitest';
import BBoxOverlay, { computeOverlayBox } from '../src/components/drawings/BBoxOverlay';

// Decision (Task 23, controller ruling 5): BBoxOverlay takes the project's normalized [x, y, w, h] (0..1, top-left
// origin) by default and accepts units="px" for pixel-space boxes. The plan's test is kept verbatim below; it passes
// because [900,0,100,100] is far outside the 0..1 page. The px variant and the normalized [1.1, 0, 0.1, 0.1] case give
// the same check with bbox_source "ground_truth", so out-of-bounds is the only reason for the label.

test('clamps bbox to page bounds and marks approximate', () => {
  const { getByText } = render(<BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[900, 0, 100, 100]} />);
  expect(getByText(/approximate/i)).toBeInTheDocument();
});

describe('BBoxOverlay', () => {
  it('pixel units: clamps an off-page box into the page and labels it approximate (ground truth source)', () => {
    const { getByText, getByTestId } = render(
      <BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[900, 0, 100, 100]} units="px" source="ground_truth" />,
    );
    expect(getByText(/approximate/i)).toBeInTheDocument();
    const box = getByTestId('bbox-rect');
    const left = parseFloat(box.style.left);
    const width = parseFloat(box.style.width);
    expect(left + width).toBeLessThanOrEqual(800);
    expect(left).toBeGreaterThanOrEqual(0);
  });

  it('normalized out-of-bounds [1.1, 0, 0.1, 0.1] is clamped and approximate', () => {
    const { getByText } = render(
      <BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[1.1, 0, 0.1, 0.1]} source="ground_truth" />,
    );
    expect(getByText(/approximate/i)).toBeInTheDocument();
    const b = computeOverlayBox({ w: 800, h: 1000 }, [1.1, 0, 0.1, 0.1]);
    expect(b.outOfBounds).toBe(true);
    expect(b.left + b.width).toBeLessThanOrEqual(800);
  });

  it('covers more than 25% of the page area -> approximate', () => {
    const { getByText } = render(
      <BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[0.0312, 0.4587, 0.6295, 0.45]} source="ground_truth" />,
    );
    expect(getByText(/approximate/i)).toBeInTheDocument();
  });

  it('whole-page box from bbox_source "page" -> approximate', () => {
    const { getByText } = render(<BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[0, 0, 1, 1]} source="page" />);
    expect(getByText(/approximate/i)).toBeInTheDocument();
  });

  it('small in-bounds box that is not ground truth (parse_element) -> approximate', () => {
    const { getByText } = render(
      <BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[0.26, 0.43, 0.04, 0.03]} source="parse_element" />,
    );
    expect(getByText(/approximate/i)).toBeInTheDocument();
  });

  it('small in-bounds ground-truth box is exact: scaled by page px, no approximate label', () => {
    const { queryByText, getByTestId } = render(
      <BBoxOverlay page={{ w: 800, h: 1000 }} bbox={[0.25, 0.5, 0.1, 0.05]} source="ground_truth" />,
    );
    expect(queryByText(/approximate/i)).toBeNull();
    const box = getByTestId('bbox-rect');
    expect(box.style.left).toBe('200px');
    expect(box.style.top).toBe('500px');
    expect(box.style.width).toBe('80px');
    expect(box.style.height).toBe('50px');
  });
});

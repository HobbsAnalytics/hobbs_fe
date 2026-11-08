import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

describe('App shell', () => {
  it('renders the sidebar logo block and the co-pilot placeholder at /', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getAllByText('Blue Ridge LNG').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('BR')).toBeInTheDocument();
    expect(screen.getByText('Project Intelligence')).toBeInTheDocument();
    expect(screen.getByTestId('page-copilot')).toBeInTheDocument();
  });

  it('routes /compliance and /drawings/:id to their placeholders', () => {
    const { unmount } = render(
      <MemoryRouter initialEntries={['/compliance']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId('page-compliance')).toBeInTheDocument();
    unmount();
    render(
      <MemoryRouter initialEntries={['/drawings/DWG-001']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId('page-drawing')).toHaveTextContent('DWG-001');
  });
});

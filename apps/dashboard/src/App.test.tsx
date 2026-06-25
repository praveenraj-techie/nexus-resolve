import { render, screen } from '@testing-library/react';
import App from './App';

vi.mock('./replay', () => ({
  loadReplayEvents: vi.fn(async () => []),
  playReplayEvents: vi.fn(() => () => undefined),
}));

vi.mock('./api', () => ({
  healthCheck: vi.fn(async () => false),
  startIncident: vi.fn(),
  approveRun: vi.fn(),
  rejectRun: vi.fn(),
  connectRunStream: vi.fn(),
}));

describe('App', () => {
  it('renders the operations console as the first screen', async () => {
    render(<App />);

    expect(screen.getByText('NEXUS-RESOLVE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /ticket details/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /agent timeline/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /policy checks/i })).toBeInTheDocument();
  });
});


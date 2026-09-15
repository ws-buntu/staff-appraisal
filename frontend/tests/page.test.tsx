import { expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import Page from '../app/page';

test('does not offer appraisal actions before authentication and workflows exist', () => {
  render(<Page />);
  expect(screen.getByRole('heading', { name: 'Staff Appraisal' })).toBeTruthy();
  expect(screen.queryByRole('button')).toBeNull();
  expect(screen.getByRole('status').textContent).toContain('Foundation');
});

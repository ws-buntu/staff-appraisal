import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Staff Appraisal',
  description: 'Staff performance planning, review and appraisal. Foundation under development.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

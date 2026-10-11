import Link from 'next/link';
export default function NotFound() {
  return (
    <main id="main" className="route-error">
      <h1>Page not found</h1>
      <p>The page you requested isn’t available.</p>
      <Link className="button primary" href="/">
        Return to verification
      </Link>
    </main>
  );
}

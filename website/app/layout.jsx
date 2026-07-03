import "./globals.css";
import { SITE_URL, GITHUB, HUGGINGFACE } from "../lib/content";

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "sup computer",
    template: "%s · sup computer",
  },
  description: "a small language model studio",
  openGraph: {
    siteName: "sup computer",
    type: "website",
    url: "/",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">skip to content</a>
        <header className="masthead" id="top">
          <div className="masthead__brand">
            {/* a <p>, not <h1>: each page owns its single h1 */}
            <p className="masthead__title"><a href="/">sup computer</a></p>
            <p className="masthead__tagline">a small language model studio</p>
          </div>
          <nav className="masthead__nav">
            <a className="masthead__link" href="/#models">models</a>
            <a className="masthead__link" href="/#research">research</a>
            <a className="masthead__link" href="/model-player/">player</a>
          </nav>
        </header>
        <hr />
        <main id="main">{children}</main>
        <footer className="footer">
          <span className="footer__colophon">
            sup computer · led by <a className="footer__link" href="https://romellogoodman.com/">romello goodman</a>
          </span>
          <span className="footer__links">
            <a className="footer__link" href={HUGGINGFACE}>huggingface</a>
            <a className="footer__link" href={GITHUB}>sourcecode</a>
            <a className="footer__link" href="#top">back to top ↑</a>
          </span>
        </footer>
      </body>
    </html>
  );
}

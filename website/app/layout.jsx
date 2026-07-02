import "./globals.css";
import { SITE_URL } from "../lib/content";

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
        <header className="masthead" id="top">
          <div className="masthead__brand">
            <h1 className="masthead__title"><a href="/">sup computer</a></h1>
            <p className="masthead__tagline">a small language model studio</p>
          </div>
          <nav className="masthead__nav">
            <a className="masthead__link" href="/#models">models</a>
            <a className="masthead__link" href="/#research">research</a>
            <a className="masthead__link" href="https://github.com/romellogoodman/sup-computer">view source</a>
          </nav>
        </header>
        <hr />
        <main>{children}</main>
        <footer className="footer">
          <span className="footer__colophon">
            sup computer · a small language model studio ·{" "}
            <a className="footer__link" href="https://github.com/romellogoodman/sup-computer">view source on github</a>
          </span>
          <a className="footer__link" href="#top">back to top ↑</a>
        </footer>
      </body>
    </html>
  );
}

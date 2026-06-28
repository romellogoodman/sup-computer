import "./globals.css";

export const metadata = {
  title: "sup computer",
  description: "a small language model studio",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <header className="masthead">
          <h1><a href="/">sup computer</a></h1>
          <p className="tagline">a small language model studio</p>
          <nav className="top">
            <a href="/#models">models</a>
            <a href="/#research">research</a>
            <a href="https://github.com/romellogoodman/sup-computer">view source</a>
          </nav>
        </header>
        <hr />
        <main>{children}</main>
      </body>
    </html>
  );
}

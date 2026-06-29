export const metadata = {
  title: "Page not found — sup computer",
};

export default function NotFound() {
  return (
    <>
      <p className="notfound__label">404 · not found</p>
      <h1 className="notfound__title">Page not found</h1>
      <p className="measure">
        There is no page at this address. It may have moved, or it may never
        have existed — the notebook only keeps what was written down.
      </p>
      <p>
        <a href="/">← back to the front page</a>
      </p>
    </>
  );
}

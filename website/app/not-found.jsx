export const metadata = {
  title: "Page not found — sup computer",
};

export default function NotFound() {
  return (
    <>
      <h2>Page not found</h2>
      <p>
        There is no page at this address. It may have moved, or it may never
        have existed — the notebook only keeps what was written down.
      </p>
      <p>
        <a href="/">Back to the front page</a>.
      </p>
    </>
  );
}

"use client";

// The demoted model card on a series page: a <details> that is open on a
// wide screen and collapsed on a phone. The HTML ships open (the reader
// with no JS gets everything); the effect closes it once, on mount, when the
// viewport is narrow.

import { useEffect, useRef } from "react";

export default function CardDetails({ summary, children }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && window.matchMedia("(max-width: 760px)").matches) {
      ref.current.open = false;
    }
  }, []);
  return (
    <details className="card" open ref={ref}>
      <summary className="card__summary">{summary}</summary>
      <div className="card__body">{children}</div>
    </details>
  );
}

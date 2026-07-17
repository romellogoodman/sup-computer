"use client";
import { useRef, useState } from "react";

// The /train prompt with its copy affordance — the page's one interactive
// element. `text` is the raw fenced-block content from train.md, so what you
// copy is byte-for-byte what the file says regardless of display wrapping.
export default function PromptBlock({ text }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable (permissions, insecure context) — the text
      // below stays selectable, so fail quiet rather than alarm
    }
  };
  return (
    <div className="prompt-block">
      <div className="prompt-block__bar">
        <span className="prompt-block__label">the prompt</span>
        <button className="prompt-block__copy" type="button" onClick={copy}>
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <pre className="prompt-block__pre">{text}</pre>
    </div>
  );
}

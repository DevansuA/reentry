"use client";

import { useState } from "react";

interface Props {
  text: string;
}

export function CopyButton({ text }: Props) {
  const [copied, setCopied] = useState(false);

  async function handleClick() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available in some contexts.
    }
  }

  return (
    <button
      className={`copy-btn ${copied ? "copied" : ""}`}
      onClick={handleClick}
      aria-label="Copy to clipboard"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

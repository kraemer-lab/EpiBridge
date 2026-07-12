"use client";

import { useState, useRef, useEffect } from "react";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function CollapsibleSection({ title, defaultOpen = false, children }: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(defaultOpen ? null : 0);
  const initialized = useRef(false);

  useEffect(() => {
    if (defaultOpen && contentRef.current && !initialized.current) {
      initialized.current = true;
      setHeight(contentRef.current.scrollHeight);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open && contentRef.current && initialized.current) {
      setHeight(contentRef.current.scrollHeight);
    }
  }, [open]);

  const handleToggle = () => {
    if (!contentRef.current) return;
    initialized.current = true;
    if (open) {
      const h = contentRef.current.scrollHeight;
      setHeight(h);
      requestAnimationFrame(() => {
        setHeight(0);
      });
      setOpen(false);
    } else {
      setHeight(contentRef.current.scrollHeight);
      setOpen(true);
    }
  };

  return (
    <div className="collapsible-section">
      <button
        className="collapsible-header"
        onClick={handleToggle}
        aria-expanded={open}
      >
        <span className="collapsible-title">{title}</span>
        <span className={`collapsible-chevron${open ? " open" : ""}`}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>
      <div
        className="collapsible-content"
        style={{ height: height !== null ? `${height}px` : undefined }}
      >
        <div ref={contentRef} className="collapsible-inner">
          {children}
        </div>
      </div>
    </div>
  );
}

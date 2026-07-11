"use client";

import { useEffect, useRef } from "react";

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
}

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return false;
  const inner = trimmed.slice(1, -1).trim();
  if (!inner) return false;
  return /^[\s\-:|]+$/.test(inner);
}

export function renderMarkdown(md: string): string {
  const lines = md.split("\n");
  const html: string[] = [];
  let inCode = false;
  let codeLang = "";
  let codeLines: string[] = [];
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];
  let inList = false;
  let listType: "ul" | "ol" | null = null;

  function closeList() {
    if (inList) {
      html.push(`</${listType}>`);
      inList = false;
      listType = null;
    }
  }

  function openList(type: "ul" | "ol") {
    closeList();
    inList = true;
    listType = type;
    html.push(`<${type}>`);
  }

  function closeTable() {
    if (!inTable) return;
    html.push("<table><thead><tr>");
    for (const h of tableHeaders) {
      html.push(`<th>${renderInline(h)}</th>`);
    }
    html.push("</tr></thead><tbody>");
    for (const row of tableRows) {
      html.push("<tr>");
      for (const cell of row) {
        html.push(`<td>${renderInline(cell)}</td>`);
      }
      html.push("</tr>");
    }
    html.push("</tbody></table>");
    inTable = false;
    tableHeaders = [];
    tableRows = [];
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("```")) {
      if (inCode) {
        const escaped = escapeHtml(codeLines.join("\n"));
        const langAttr = codeLang ? ` data-lang="${escapeHtml(codeLang)}"` : "";
        html.push(`<pre><code${langAttr}>${escaped}</code></pre>`);
        inCode = false;
        codeLang = "";
        codeLines = [];
      } else {
        closeList();
        closeTable();
        inCode = true;
        codeLang = line.slice(3).trim();
      }
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      if (isTableSeparator(line)) continue;

      const cells = line.split("|").filter((c) => c.trim()).map((c) => c.trim());

      if (!inTable) {
        closeList();
        inTable = true;
        tableHeaders = cells;
        tableRows = [];
      } else {
        tableRows.push(cells);
      }
      continue;
    }

    closeTable();

    if (line.trim() === "") {
      closeList();
      continue;
    }

    if (/^-{3,}$/.test(line.trim())) {
      closeList();
      html.push("<hr />");
      continue;
    }

    if (line.startsWith("### ")) {
      closeList();
      html.push(`<h3>${renderInline(line.slice(4).trim())}</h3>`);
      continue;
    }
    if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${renderInline(line.slice(3).trim())}</h2>`);
      continue;
    }
    if (line.startsWith("# ")) {
      closeList();
      html.push(`<h1>${renderInline(line.slice(2).trim())}</h1>`);
      continue;
    }

    if (line.startsWith("> ")) {
      closeList();
      html.push(`<blockquote><p>${renderInline(line.slice(2))}</p></blockquote>`);
      continue;
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList || listType !== "ul") openList("ul");
      html.push(`<li>${renderInline(line.slice(2))}</li>`);
      continue;
    }

    if (/^\d+\.\s/.test(line)) {
      if (!inList || listType !== "ol") openList("ol");
      html.push(`<li>${renderInline(line.replace(/^\d+\.\s*/, ""))}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInline(line)}</p>`);
  }

  if (inCode) {
    const escaped = escapeHtml(codeLines.join("\n"));
    const langAttr = codeLang ? ` data-lang="${escapeHtml(codeLang)}"` : "";
    html.push(`<pre><code${langAttr}>${escaped}</code></pre>`);
  }
  closeTable();
  closeList();

  return html.join("\n");
}

export function Markdown({ content }: { content: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const pres = container.querySelectorAll<HTMLPreElement>("pre");
    pres.forEach((pre) => {
      if (pre.parentElement?.classList.contains("code-block")) return;

      const wrapper = document.createElement("div");
      wrapper.className = "code-block";

      const header = document.createElement("div");
      header.className = "code-block-header";

      const code = pre.querySelector("code");
      const lang = code?.getAttribute("data-lang");
      if (lang) {
        const langLabel = document.createElement("span");
        langLabel.className = "code-block-lang";
        langLabel.textContent = lang;
        header.appendChild(langLabel);
      }

      const spacer = document.createElement("span");
      spacer.style.flex = "1";
      header.appendChild(spacer);

      const btn = document.createElement("button");
      btn.className = "code-block-copy";
      btn.textContent = "Copy";
      btn.addEventListener("click", () => {
        const text = pre.textContent || "";
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = "Copied";
          setTimeout(() => { btn.textContent = "Copy"; }, 2000);
        });
      });
      header.appendChild(btn);

      wrapper.appendChild(header);
      if (pre.parentNode) {
        pre.parentNode.insertBefore(wrapper, pre);
      }
      wrapper.appendChild(pre);
    });
  });

  return (
    <div
      ref={containerRef}
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}

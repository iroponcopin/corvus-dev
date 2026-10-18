import { Fragment, type ReactNode } from "react";

/**
 * The wiki's inline markup, and nothing more: `<b>`, `<i>`, `<code>`, `<br>`, `**bold**` and
 * `{@code x}`. A tag that is not one of these, or that has no closing partner, stays literal
 * text. Every piece of text goes through React, so nothing here can inject HTML.
 */

type Kind = "b" | "i" | "code";

const TOKEN = /<(b|i|code)>|<\/(b|i|code)>|<br\s*\/?>|\*\*|\{@code\s+([^{}]+?)\}/;

function wrap(kind: Kind, children: ReactNode, key: number): ReactNode {
  if (kind === "b") return <strong key={key}>{children}</strong>;
  if (kind === "i") return <em key={key}>{children}</em>;
  return <code key={key}>{children}</code>;
}

function render(text: string, keyBase: number): ReactNode[] {
  const out: ReactNode[] = [];
  let rest = text;
  let key = keyBase;
  while (rest.length > 0) {
    const m = TOKEN.exec(rest);
    if (m === null) {
      out.push(<Fragment key={key++}>{rest}</Fragment>);
      break;
    }
    if (m.index > 0) out.push(<Fragment key={key++}>{rest.slice(0, m.index)}</Fragment>);
    const after = rest.slice(m.index + m[0].length);
    rest = after;
    if (m[0].startsWith("<br")) {
      out.push(<br key={key++} />);
      continue;
    }
    if (m[3] !== undefined) {
      out.push(<code key={key++}>{m[3]}</code>);
      continue;
    }
    if (m[0] === "**") {
      const end = after.indexOf("**");
      if (end < 0) {
        out.push(<Fragment key={key++}>**</Fragment>);
        continue;
      }
      out.push(wrap("b", render(after.slice(0, end), key), key));
      key += 1;
      rest = after.slice(end + 2);
      continue;
    }
    if (m[1] !== undefined) {
      const kind = m[1] as Kind;
      const close = `</${kind}>`;
      const end = after.indexOf(close);
      if (end < 0) {
        out.push(<Fragment key={key++}>{m[0]}</Fragment>);
        continue;
      }
      const inner = after.slice(0, end);
      const node = kind === "code" ? <code key={key}>{inner}</code> : wrap(kind, render(inner, key * 10), key);
      out.push(node);
      key += 1;
      rest = after.slice(end + close.length);
      continue;
    }
    // A stray closing tag stays literal text.
    out.push(<Fragment key={key++}>{m[0]}</Fragment>);
  }
  return out;
}

export function Rich({ text }: { text: string }): ReactNode {
  return <>{render(text, 0)}</>;
}

/**
 * Trusted HTML that comes from the wiki's own bundles (e.g. the launcher guide's body_html, the
 * Discord steps' <code>): rendered as written, because it is the repository's copy, not input.
 */
export function TrustedHtml({ html, className, as: Tag = "div" }: { html: string; className?: string; as?: "div" | "p" | "span" }) {
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

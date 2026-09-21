// A deliberately small Markdown renderer for chat answers.
//
// Framework has no `md` tagged template in JS scope, and the model only ever emits a
// narrow subset (bold, italic, code, lists, links, ### headings). Pulling in a full
// parser for that would be the only runtime dependency on the site, so this handles
// the subset instead and renders anything it doesn't know as plain text.
//
// Safety: the source text is escaped FIRST, then the formatting patterns are applied
// to the escaped string. Nothing the model writes can become markup it didn't earn,
// and link hrefs are restricted to http(s) and same-site relative paths.

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

// Applied to already-escaped text, innermost first so a link label can hold bold.
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, (_, c) => `<code>${c}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, (_, c) => `<strong>${c}</strong>`)
    .replace(/(^|[^*])\*([^*]+)\*/g, (_, pre, c) => `${pre}<em>${c}</em>`)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, text, href) =>
      /^(https?:\/\/|\.\/|\/|\?)/.test(href) ? `<a href="${href}">${text}</a>` : m);
}

export function renderMarkdown(text) {
  const root = document.createElement("div");
  const blocks = String(text ?? "").trim().split(/\n{2,}/);

  for (const block of blocks) {
    const lines = block.split("\n");

    // Lists: every line has to be a bullet (or every line numbered), otherwise it is
    // a paragraph that merely starts with a dash.
    const bullets = lines.every((l) => /^\s*[-*]\s+/.test(l));
    const numbers = lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
    if (bullets || numbers) {
      const list = document.createElement(bullets ? "ul" : "ol");
      for (const l of lines) {
        const li = document.createElement("li");
        li.innerHTML = inline(esc(l.replace(/^\s*(?:[-*]|\d+[.)])\s+/, "")));
        list.append(li);
      }
      root.append(list);
      continue;
    }

    const heading = block.match(/^(#{3,6})\s+(.*)$/);
    if (heading) {
      const h = document.createElement(`h${heading[1].length}`);
      h.innerHTML = inline(esc(heading[2]));
      root.append(h);
      continue;
    }

    const p = document.createElement("p");
    p.innerHTML = inline(esc(block).replace(/\n/g, "<br>"));
    root.append(p);
  }
  return root;
}

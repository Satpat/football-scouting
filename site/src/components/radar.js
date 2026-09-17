// Radar (spider) chart of percentile traits, drawn with d3 as plain SVG.
import * as d3 from "npm:d3";

const FONT_SIZE = 11;
const CHAR_W = FONT_SIZE * 0.56; // heuristic glyph width for the sans-serif at 11px
const LINE_H = FONT_SIZE * 1.2;

// Greedy word-wrap using an estimated character width (no DOM measurement needed).
function wrapWords(text, firstLineWidth, restWidth) {
  const words = text.split(" ");
  const lines = [];
  let line = "";
  let budget = firstLineWidth;
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (line && test.length * CHAR_W > budget) {
      lines.push(line);
      line = w;
      budget = restWidth;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export function radar(traits, {size = 320, accent = "#1e5631", levels = 4, margin = 88} = {}) {
  const n = traits.length;
  const r = size / 2 - margin;
  const cx = size / 2, cy = size / 2;
  const angle = (i) => (i / n) * 2 * Math.PI - Math.PI / 2;
  const pt = (i, v) => [cx + Math.cos(angle(i)) * r * v / 100, cy + Math.sin(angle(i)) * r * v / 100];
  const svg = d3.create("svg").attr("width", size).attr("height", size).attr("viewBox", `0 0 ${size} ${size}`)
    .attr("font-family", "var(--sans-serif)").attr("font-size", FONT_SIZE);
  // rings
  for (let l = 1; l <= levels; l++) {
    const v = (100 * l) / levels;
    svg.append("polygon").attr("points", traits.map((_, i) => pt(i, v).join(",")).join(" "))
      .attr("fill", "none").attr("stroke", "var(--theme-foreground-faint)").attr("stroke-width", 1).attr("stroke-dasharray", l === levels ? null : "3,3")
      .lower();

  }
  // axes + labels
  const safety = 8;
  traits.forEach((t, i) => {
    const [x, y] = pt(i, 100);
    svg.append("line").attr("x1", cx).attr("y1", cy).attr("x2", x).attr("y2", y).attr("stroke", "var(--theme-foreground-faint)");
    const [lx, ly] = pt(i, 118);
    const anchor = Math.abs(lx - cx) < 8 ? "middle" : lx > cx ? "start" : "end";
    const available = anchor === "middle" ? Math.min(lx, size - lx) * 2 - safety * 2
      : anchor === "start" ? size - lx - safety
      : lx - safety;
    const pctText = t.pct == null ? "–" : `${t.pct}%`;
    const firstLineWidth = Math.max(available - (pctText.length + 1) * CHAR_W, 32);
    const lines = wrapWords(t.label, firstLineWidth, Math.max(available, 32));
    const text = svg.append("text").attr("x", lx).attr("y", ly).attr("text-anchor", anchor).attr("fill", "var(--theme-foreground)");
    text.append("tspan").attr("font-weight", 700).text(`${pctText} `);
    text.append("tspan").attr("fill", "var(--theme-foreground-muted)").text(lines[0] ?? "");
    lines.slice(1).forEach((line) => {
      text.append("tspan").attr("x", lx).attr("dy", `${LINE_H}px`).attr("fill", "var(--theme-foreground-muted)").text(line);
    });
    if (lines.length > 1) text.attr("y", ly - ((lines.length - 1) * LINE_H) / 2);
  });
  // value polygon, with a node at each corner so the exact value is legible even when neighbours are close
  const pts = traits.map((t, i) => pt(i, t.pct ?? 0));
  svg.append("polygon").attr("points", pts.map((p) => p.join(",")).join(" ")).attr("fill", accent).attr("fill-opacity", 0.55).attr("stroke", accent).attr("stroke-width", 1.5);
  pts.forEach(([x, y]) => {
    svg.append("circle").attr("cx", x).attr("cy", y).attr("r", 3.5).attr("fill", accent).attr("stroke", "var(--theme-background)").attr("stroke-width", 1.5);
  });

  return svg.node();
}

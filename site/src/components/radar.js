// Radar (spider) chart of percentile traits, drawn with d3 as plain SVG.
import * as d3 from "npm:d3";

export function radar(traits, {size = 320, accent = "#1e5631", levels = 4} = {}) {
  const n = traits.length;
  const r = size / 2 - 58;
  const cx = size / 2, cy = size / 2;
  const angle = (i) => (i / n) * 2 * Math.PI - Math.PI / 2;
  const pt = (i, v) => [cx + Math.cos(angle(i)) * r * v / 100, cy + Math.sin(angle(i)) * r * v / 100];
  const svg = d3.create("svg").attr("width", size).attr("height", size).attr("viewBox", `0 0 ${size} ${size}`)
    .attr("font-family", "var(--sans-serif)").attr("font-size", 11);
  // rings
  for (let l = 1; l <= levels; l++) {
    const v = (100 * l) / levels;
    svg.append("polygon").attr("points", traits.map((_, i) => pt(i, v).join(",")).join(" "))
      .attr("fill", l === levels ? "var(--theme-background-alt)" : "none").attr("stroke", "var(--theme-foreground-faint)").attr("stroke-width", 1)
      .lower();
    svg.append("text").attr("x", cx + 3).attr("y", cy - r * v / 100 - 2).attr("fill", "var(--theme-foreground-muted)").attr("font-size", 9).text(`${v}%`);
  }
  // axes + labels
  traits.forEach((t, i) => {
    const [x, y] = pt(i, 100);
    svg.append("line").attr("x1", cx).attr("y1", cy).attr("x2", x).attr("y2", y).attr("stroke", "var(--theme-foreground-faint)");
    const [lx, ly] = pt(i, 128);
    const anchor = Math.abs(lx - cx) < 8 ? "middle" : lx > cx ? "start" : "end";
    const label = svg.append("text").attr("x", lx).attr("y", ly).attr("text-anchor", anchor).attr("fill", "var(--theme-foreground)");
    label.append("tspan").attr("x", lx).attr("dy", "-0.2em").text(t.label);
    label.append("tspan").attr("x", lx).attr("dy", "1.2em").attr("font-weight", 700).attr("fill", accent).text(t.pct == null ? "–" : `${t.pct}%`);
  });
  // value polygon
  const pts = traits.map((t, i) => pt(i, t.pct ?? 0));
  svg.append("polygon").attr("points", pts.map((p) => p.join(",")).join(" ")).attr("fill", accent).attr("fill-opacity", 0.35).attr("stroke", accent).attr("stroke-width", 2);
  pts.forEach(([x, y], i) => svg.append("circle").attr("cx", x).attr("cy", y).attr("r", 4).attr("fill", accent).append("title").text(`${traits[i].label}: ${traits[i].pct ?? "–"}%`));
  return svg.node();
}

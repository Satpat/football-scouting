// See https://observablehq.com/framework/config for documentation.
export default {
  title: "SA State League Scouting 2026",
  root: "src",
  pages: [
    {name: "Explorer", path: "/"},
    {name: "Player shortlist", path: "/shortlist"},
    {name: "Teams & ladders", path: "/teams"},
    {name: "Ask the data", path: "/chat"},
    {name: "About the data", path: "/about"},
  ],
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚽</text></svg>">',
  toc: false,
  pager: false,
  sidebar: true,
  footer: "Data: Football SA and SAASL DRIBL match centres (SL1, SL2, NPL, SAASL), enriched with Sofascore advanced event metrics and ratings for Senior NPL.",
  style: "style.css",
};

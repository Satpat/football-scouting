// Sofascore data extraction — run inside the browser pane on https://www.sofascore.com
// (Cloudflare and Varnish anti-bot block non-browser clients with TLS fingerprinting).
// Paste the entire file into the DevTools JS console, then run:
//
//   await __sofa.init();       // 1. fetches standings & round lists
//   await __sofa.events();     // 2. fetches all match events across rounds
//   await __sofa.details();    // 3. fetches lineups, incidents & stats for finished matches
//   __sofa.download();         // 4. triggers browser download of output/sofascore_raw_2026.json
//
// State is stored on window.__sofa.state so you can pause, inspect, and resume at any time.

(() => {
  const BASE = 'https://api.sofascore.com/api/v1/';
  const DELAY_MS = 250; // polite pacing to respect rate limits

  // The 7 target tournaments requested:
  const TOURNAMENTS = [
    { id: 1258,  season: 88847, name: "NPL South Australia", tier: "NPL", hasDetailedStats: true },
    { id: 26016, season: 88849, name: "South Australia State League 1", tier: "SL1", hasDetailedStats: false },
    { id: 32070, season: 88894, name: "South Australia State League 2", tier: "SL2", hasDetailedStats: false },
    { id: 32103, season: 89000, name: "South Australia State League 2 Reserves", tier: "SL2_RES", hasDetailedStats: false },
    { id: 27357, season: 76898, name: "South Australia State League 2 South", tier: "SL2_SOUTH", hasDetailedStats: false },
    { id: 34182, season: 93152, name: "South Australia Saturday Division 2", tier: "SAT_DIV2", hasDetailedStats: false },
    { id: 32825, season: 91200, name: "South Australia Saturday Premier A", tier: "SAT_PREM_A", hasDetailedStats: false },
  ];

  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const st = (window.__sofa && window.__sofa.state) || {
    standings: {},
    rounds: {},
    events: {},       // eventId -> event summary
    lineups: {},      // eventId -> full lineup & player stats
    incidents: {},    // eventId -> list of incidents (goals, assists, cards)
    statistics: {},   // eventId -> match team statistics (possession, xG)
    playerProfiles: {}, // playerId -> full bio, preferred foot, attributes
    errors: [],
  };

  async function get(path, { allow404 = false } = {}) {
    const res = await fetch(BASE + path, {
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
      }
    });
    if (res.status === 404 && allow404) {
      return null;
    }
    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}: ${path}`);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  const api = {
    state: st,
    tournaments: TOURNAMENTS,

    // Status inspector: print summary table of current extraction state
    status() {
      const finished = Object.values(st.events).filter(ev => ev.status?.type === 'finished');
      console.log('📊 Current Extraction Status:');
      console.table({
        'Tournaments in Standings': Object.keys(st.standings).length,
        'Total Matches Found': Object.keys(st.events).length,
        'Finished Matches': finished.length,
        'Lineups Extracted': Object.keys(st.lineups).length,
        'Incidents Extracted': Object.keys(st.incidents).length,
        'Team Stats Extracted': Object.keys(st.statistics).length,
        'Errors Logged': st.errors.length,
      });
      return {
        tournaments: Object.keys(st.standings).length,
        matches: Object.keys(st.events).length,
        finished: finished.length,
        lineups: Object.keys(st.lineups).length,
        incidents: Object.keys(st.incidents).length,
        stats: Object.keys(st.statistics).length,
      };
    },

    // Phase 1: Fetch standings and list of rounds for each competition
    async init() {
      console.log('⚡ Phase 1: Fetching standings and rounds...');
      for (const t of TOURNAMENTS) {
        try {
          console.log(`  Fetching standings: ${t.name}...`);
          const std = await get(`unique-tournament/${t.id}/season/${t.season}/standings/total`, { allow404: true });
          st.standings[t.id] = std?.standings || [];
        } catch (e) {
          console.warn(`  ⚠️ Could not fetch standings for ${t.name}:`, e.message);
          st.errors.push({ step: 'standings', tournament: t, error: e.message });
        }
        await sleep(DELAY_MS);

        try {
          console.log(`  Fetching rounds: ${t.name}...`);
          const rds = await get(`unique-tournament/${t.id}/season/${t.season}/rounds`, { allow404: true });
          st.rounds[t.id] = rds?.rounds || [];
        } catch (e) {
          console.warn(`  ⚠️ Could not fetch rounds for ${t.name}:`, e.message);
          st.errors.push({ step: 'rounds', tournament: t, error: e.message });
        }
        await sleep(DELAY_MS);
      }
      const totalRounds = Object.values(st.rounds).reduce((acc, r) => acc + r.length, 0);
      console.log(`✅ Phase 1 complete. Recorded ${Object.keys(st.standings).length} tournaments and ${totalRounds} total rounds.`);
      return { standings: Object.keys(st.standings).length, rounds: totalRounds };
    },

    // Phase 2: Fetch all events across all rounds
    async events() {
      console.log('⚡ Phase 2: Fetching fixtures and results across rounds...');
      for (const t of TOURNAMENTS) {
        // Sort rounds ascending (Round 1, 2, ... 22, 28, 29)
        const rawRounds = st.rounds[t.id] || [];
        const rounds = [...rawRounds].sort((a, b) => a.round - b.round);
        console.log(`\n🏆 ${t.name} (${rounds.length} rounds scheduled)`);

        for (let i = 0; i < rounds.length; i++) {
          const r = rounds[i];
          try {
            // 404 is normal for unplayed playoff rounds (e.g. 28, 29)
            const data = await get(`unique-tournament/${t.id}/season/${t.season}/events/round/${r.round}`, { allow404: true });
            const roundEvents = data?.events || [];
            if (roundEvents.length > 0) {
              for (const ev of roundEvents) {
                if (ev && ev.id) {
                  st.events[ev.id] = {
                    id: ev.id,
                    customId: ev.customId,
                    slug: ev.slug,
                    tournamentId: t.id,
                    tournamentName: t.name,
                    tier: t.tier,
                    seasonId: t.season,
                    round: r.round,
                    status: ev.status,
                    startTimestamp: ev.startTimestamp,
                    homeTeam: { id: ev.homeTeam?.id, name: ev.homeTeam?.name, shortName: ev.homeTeam?.shortName },
                    awayTeam: { id: ev.awayTeam?.id, name: ev.awayTeam?.name, shortName: ev.awayTeam?.shortName },
                    homeScore: ev.homeScore,
                    awayScore: ev.awayScore,
                    winnerCode: ev.winnerCode,
                    hasDetailedStats: t.hasDetailedStats,
                  };
                }
              }
              console.log(`  [${i + 1}/${rounds.length}] Round ${r.round}: ✅ ${roundEvents.length} matches (Total collected: ${Object.keys(st.events).length})`);
            } else {
              console.log(`  [${i + 1}/${rounds.length}] Round ${r.round}: ⚪ 0 matches (playoffs/unplayed)`);
            }
          } catch (e) {
            console.warn(`  ⚠️ Error fetching round ${r.round} for ${t.name}:`, e.message);
            st.errors.push({ step: 'round_events', tournament: t, round: r.round, error: e.message });
          }
          await sleep(DELAY_MS);
        }
      }
      console.log(`\n✅ Phase 2 complete. Collected ${Object.keys(st.events).length} matches across all competitions.`);
      return Object.keys(st.events).length;
    },

    // Phase 3: Fetch lineups, incidents, and team stats for finished matches
    async details() {
      const finishedEvents = Object.values(st.events).filter(ev => ev.status?.type === 'finished');
      console.log(`\n⚡ Phase 3: Fetching details for ${finishedEvents.length} finished matches...`);

      let done = 0;
      for (const ev of finishedEvents) {
        done++;
        const homeName = ev.homeTeam?.name || 'Home';
        const awayName = ev.awayTeam?.name || 'Away';

        // 1. Match Incidents (goals, assists, cards, substitutions)
        if (!st.incidents[ev.id]) {
          try {
            const inc = await get(`event/${ev.id}/incidents`, { allow404: true });
            st.incidents[ev.id] = inc?.incidents || [];
          } catch (e) {
            if (e.status !== 403 && e.status !== 404) {
              st.errors.push({ step: 'incidents', eventId: ev.id, error: e.message });
            }
          }
          await sleep(DELAY_MS);
        }

        // 2. Lineups & Player Stats (primarily NPL matches)
        if (ev.hasDetailedStats && !st.lineups[ev.id]) {
          try {
            const lu = await get(`event/${ev.id}/lineups`, { allow404: true });
            if (lu) {
              st.lineups[ev.id] = {
                confirmed: lu.confirmed,
                home: lu.home,
                away: lu.away,
              };
            }
          } catch (e) {
            if (e.status !== 403 && e.status !== 404) {
              st.errors.push({ step: 'lineups', eventId: ev.id, error: e.message });
            }
          }
          await sleep(DELAY_MS);
        }

        // 3. Match Team Statistics (possession, xG, shots, fouls)
        if (ev.hasDetailedStats && !st.statistics[ev.id]) {
          try {
            const stats = await get(`event/${ev.id}/statistics`, { allow404: true });
            st.statistics[ev.id] = stats?.statistics || [];
          } catch (e) {
            if (e.status !== 403 && e.status !== 404) {
              st.errors.push({ step: 'statistics', eventId: ev.id, error: e.message });
            }
          }
          await sleep(DELAY_MS);
        }

        if (done % 10 === 0 || done === finishedEvents.length) {
          console.log(`  [${done}/${finishedEvents.length}] ${homeName} vs ${awayName} -> Total lineups: ${Object.keys(st.lineups).length}, incidents: ${Object.keys(st.incidents).length}`);
        }
      }

      console.log(`\n✅ Phase 3 complete.`);
      console.log(`   Lineups collected: ${Object.keys(st.lineups).length}`);
      console.log(`   Incidents collected: ${Object.keys(st.incidents).length}`);
      console.log(`   Statistics collected: ${Object.keys(st.statistics).length}`);
      return {
        lineups: Object.keys(st.lineups).length,
        incidents: Object.keys(st.incidents).length,
        statistics: Object.keys(st.statistics).length,
      };
    },

    // Phase 3b: Fetch detailed player profiles (preferred foot, contract, attribute-overviews)
    async players() {
      const playerMap = new Map();
      for (const lu of Object.values(st.lineups)) {
        for (const side of ['home', 'away']) {
          for (const p of lu[side]?.players || []) {
            const sp = p.player;
            if (sp && sp.id && !playerMap.has(sp.id)) {
              playerMap.set(sp.id, sp);
            }
          }
        }
      }
      console.log(`\n⚡ Phase 3b: Fetching profile details for ${playerMap.size} unique players...`);
      st.playerProfiles = st.playerProfiles || {};
      let i = 0;
      for (const [pid, sp] of playerMap.entries()) {
        i++;
        if (!st.playerProfiles[pid]) {
          try {
            const bio = await get(`player/${pid}`, { allow404: true });
            const attrs = await get(`player/${pid}/attribute-overviews`, { allow404: true });
            st.playerProfiles[pid] = {
              ...(bio?.player || {}),
              attributes: attrs?.playerAttributeOverviews || null,
            };
          } catch (e) {
            st.errors.push({ step: 'player_profile', playerId: pid, error: e.message });
          }
          await sleep(DELAY_MS);
        }
        if (i % 25 === 0 || i === playerMap.size) {
          console.log(`  [${i}/${playerMap.size}] Fetched profile for ${sp.name || pid}`);
        }
      }
      console.log(`✅ Phase 3b complete. Collected ${Object.keys(st.playerProfiles).length} player profiles.`);
      return Object.keys(st.playerProfiles).length;
    },

    // Phase 4: Download JSON file directly to Downloads
    download(filename = 'sofascore_raw_2026.json') {
      const payload = {
        extracted_at: new Date().toISOString(),
        tournaments: TOURNAMENTS,
        standings: st.standings,
        rounds: st.rounds,
        events: st.events,
        lineups: st.lineups,
        incidents: st.incidents,
        statistics: st.statistics,
        playerProfiles: st.playerProfiles,
        errors: st.errors,
      };

      const jsonStr = JSON.stringify(payload, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      console.log(`💾 Downloaded ${filename} (${(blob.size / 1024 / 1024).toFixed(2)} MB). Move it to the 'output/' directory.`);
      return `Downloaded ${filename}`;
    },

    // Convenience run-all method
    async runAll() {
      await api.init();
      await api.events();
      await api.details();
      await api.players();
      api.download();
    }
  };

  window.__sofa = api;
  console.log('✅ Sofascore extraction helper loaded on window.__sofa');
  console.log('Available commands:');
  console.log('  await __sofa.runAll()   -> Run all phases & auto-download');
  console.log('  __sofa.status()         -> Inspect current memory state');
  console.log('  await __sofa.details()  -> Run only Phase 3 (lineups/incidents)');
  console.log('  await __sofa.players()  -> Run only Phase 3b (player profiles & attributes)');
  console.log('  __sofa.download()       -> Download sofascore_raw_2026.json');
  return 'ready';
})();

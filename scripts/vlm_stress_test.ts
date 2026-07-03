/**
 * VLM Stress Test — Vigie Bot
 *
 * Run 100 VLM calls on a fixed screenshot, then repeat.
 * Measure: latency (p50/p95/p99), token usage, response stability.
 *
 * Usage:
 *   npx tsx /home/z/my-project/scripts/vlm_stress_test.ts
 *
 * Outputs:
 *   /home/z/my-project/scripts/vlm_stress_run1.json
 *   /home/z/my-project/scripts/vlm_stress_run2.json
 *   /home/z/my-project/scripts/vlm_stress_report.md
 */

import ZAI from 'z-ai-web-dev-sdk';
import * as fs from 'fs';
import * as path from 'path';

// ---------- Config ----------
const SCREENSHOT_PATH = '/home/z/my-project/scripts/vigie_screenshot.png';
const NUM_CALLS = 100;
const RUNS = 2;
const OUTPUT_DIR = '/home/z/my-project/scripts';
const REPORT_PATH = path.join(OUTPUT_DIR, 'vlm_stress_report.md');

const SYSTEM_PROMPT = `Tu es Vigie-VLM, un assistant visuel dédié à l'analyse de captures d'écran du bot Slack Vigie (prévention des décès par isolation pendant les canicules).

Ta mission : analyser une capture d'écran et produire un rapport structuré contenant :
1. COVERAGE_PERCENT: pourcentage de couverture affiché (ou "N/A")
2. AVG_LATENCY_MIN: latence moyenne de check-in affichée en minutes (ou "N/A")
3. L2_COUNT: nombre d'escalades L2 (pas de réponse)
4. L3_COUNT: nombre d'escalades L3 (inconscient)
5. CRISIS_MSG_COUNT: nombre de messages dans #cellule-crise
6. TOP_SECTORS: liste des secteurs visibles (JSON array)
7. ACTIVE_ALERTS: bénéficiaires actuellement en alerte (JSON array d'objets {name, level})
8. DASHBOARD_HEALTH: "OK" si coverage >= 90% ET L3=0, sinon "ALERT"
9. SUMMARY: 1 phrase en français résumant l'état global

Réponds UNIQUEMENT en JSON valide, sans texte autour.`;

interface CallResult {
  index: number;
  ok: boolean;
  latencyMs: number;
  content?: string;
  parsed?: any;
  error?: string;
}

interface RunResult {
  run: number;
  startedAt: string;
  endedAt: string;
  totalMs: number;
  results: CallResult[];
  stats: {
    successRate: number;
    p50Ms: number;
    p95Ms: number;
    p99Ms: number;
    avgMs: number;
    minMs: number;
    maxMs: number;
    parseRate: number;
    uniqueResponses: number;
    responseHashCounts: Record<string, number>;
  };
}

// ---------- Helpers ----------
function loadScreenshotAsBase64(): string {
  if (!fs.existsSync(SCREENSHOT_PATH)) {
    throw new Error(`Screenshot not found: ${SCREENSHOT_PATH}`);
  }
  const buf = fs.readFileSync(SCREENSHOT_PATH);
  return `data:image/png;base64,${buf.toString('base64')}`;
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(Math.floor((p / 100) * sorted.length), sorted.length - 1);
  return sorted[idx];
}

function hashStr(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = (h * 33) ^ s.charCodeAt(i);
  }
  return (h >>> 0).toString(16);
}

async function callVlm(zai: any, b64: string): Promise<CallResult> {
  const start = Date.now();
  try {
    const response = await zai.chat.completions.createVision({
      messages: [
        {
          role: 'system',
          content: [{ type: 'text', text: SYSTEM_PROMPT }]
        },
        {
          role: 'user',
          content: [
            { type: 'text', text: 'Analyse cette capture du dashboard Vigie et réponds en JSON.' },
            { type: 'image_url', image_url: { url: b64 } }
          ]
        }
      ],
      thinking: { type: 'disabled' }
    });
    const latencyMs = Date.now() - start;
    const content = response.choices?.[0]?.message?.content ?? '';
    let parsed: any = undefined;
    try {
      // Try to extract JSON from possibly-wrapped response
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      parsed = jsonMatch ? JSON.parse(jsonMatch[0]) : undefined;
    } catch {
      parsed = undefined;
    }
    return { index: 0, ok: true, latencyMs, content, parsed };
  } catch (err: any) {
    return {
      index: 0,
      ok: false,
      latencyMs: Date.now() - start,
      error: err?.message ?? String(err)
    };
  }
}

async function runPass(zai: any, b64: string, runNum: number): Promise<RunResult> {
  const startedAt = new Date().toISOString();
  const startTotal = Date.now();
  const results: CallResult[] = [];

  console.log(`\n=== Run ${runNum} — ${NUM_CALLS} VLM calls ===`);

  for (let i = 0; i < NUM_CALLS; i++) {
    const r = await callVlm(zai, b64);
    r.index = i;
    results.push(r);

    if (i % 10 === 0 || i === NUM_CALLS - 1) {
      const ok = results.filter(r => r.ok).length;
      const last = results[results.length - 1];
      console.log(
        `  [${i + 1}/${NUM_CALLS}] ok=${ok} last=${last.latencyMs}ms ${
          last.ok ? '' : 'ERR=' + (last.error ?? '').slice(0, 80)
        }`
      );
    }
  }

  const totalMs = Date.now() - startTotal;
  const endedAt = new Date().toISOString();

  const okResults = results.filter(r => r.ok);
  const latencies = okResults.map(r => r.latencyMs).sort((a, b) => a - b);
  const parseCount = okResults.filter(r => r.parsed !== undefined).length;
  const responseHashCounts: Record<string, number> = {};
  for (const r of okResults) {
    const h = hashStr(r.content ?? '');
    responseHashCounts[h] = (responseHashCounts[h] ?? 0) + 1;
  }

  const stats = {
    successRate: okResults.length / results.length,
    p50Ms: percentile(latencies, 50),
    p95Ms: percentile(latencies, 95),
    p99Ms: percentile(latencies, 99),
    avgMs: latencies.reduce((a, b) => a + b, 0) / Math.max(1, latencies.length),
    minMs: latencies[0] ?? 0,
    maxMs: latencies[latencies.length - 1] ?? 0,
    parseRate: parseCount / Math.max(1, okResults.length),
    uniqueResponses: Object.keys(responseHashCounts).length,
    responseHashCounts
  };

  console.log(`  -> Run ${runNum} done in ${(totalMs / 1000).toFixed(1)}s`);
  console.log(`     success=${stats.successRate} p50=${stats.p50Ms}ms p95=${stats.p95Ms}ms parse=${stats.parseRate}`);
  console.log(`     unique responses=${stats.uniqueResponses} (out of ${okResults.length})`);

  return { run: runNum, startedAt, endedAt, totalMs, results, stats };
}

function buildReport(runs: RunResult[]): string {
  const r1 = runs[0];
  const r2 = runs[1];

  const topHash1 = Object.entries(r1.stats.responseHashCounts).sort((a, b) => b[1] - a[1])[0];
  const topHash2 = Object.entries(r2.stats.responseHashCounts).sort((a, b) => b[1] - a[1])[0];

  // Sample a parsed response from each run
  const sample1 = r1.results.find(r => r.parsed)?.parsed;
  const sample2 = r2.results.find(r => r.parsed)?.parsed;

  const latencyDrift = ((r2.stats.avgMs - r1.stats.avgMs) / r1.stats.avgMs) * 100;

  let md = `# VLM Stress Test Report — Vigie Bot\n\n`;
  md += `**Date:** ${new Date().toISOString()}\n`;
  md += `**Screenshot:** \`${SCREENSHOT_PATH}\`\n`;
  md += `**Configuration:** ${NUM_CALLS} calls × ${RUNS} runs = ${NUM_CALLS * RUNS} total VLM calls\n\n`;

  md += `## 1. Summary\n\n`;
  md += `| Metric | Run 1 | Run 2 | Drift |\n`;
  md += `|---|---|---|---|\n`;
  md += `| Success rate | ${(r1.stats.successRate * 100).toFixed(1)}% | ${(r2.stats.successRate * 100).toFixed(1)}% | ${((r2.stats.successRate - r1.stats.successRate) * 100).toFixed(1)} pts |\n`;
  md += `| Parse rate (JSON valid) | ${(r1.stats.parseRate * 100).toFixed(1)}% | ${(r2.stats.parseRate * 100).toFixed(1)}% | ${((r2.stats.parseRate - r1.stats.parseRate) * 100).toFixed(1)} pts |\n`;
  md += `| Avg latency | ${r1.stats.avgMs.toFixed(0)} ms | ${r2.stats.avgMs.toFixed(0)} ms | ${latencyDrift.toFixed(1)}% |\n`;
  md += `| p50 latency | ${r1.stats.p50Ms} ms | ${r2.stats.p50Ms} ms | - |\n`;
  md += `| p95 latency | ${r1.stats.p95Ms} ms | ${r2.stats.p95Ms} ms | - |\n`;
  md += `| p99 latency | ${r1.stats.p99Ms} ms | ${r2.stats.p99Ms} ms | - |\n`;
  md += `| Min latency | ${r1.stats.minMs} ms | ${r2.stats.minMs} ms | - |\n`;
  md += `| Max latency | ${r1.stats.maxMs} ms | ${r2.stats.maxMs} ms | - |\n`;
  md += `| Total wall clock | ${(r1.totalMs / 1000).toFixed(1)} s | ${(r2.totalMs / 1000).toFixed(1)} s | - |\n`;
  md += `| Unique response hashes | ${r1.stats.uniqueResponses} | ${r2.stats.uniqueResponses} | - |\n`;
  md += `| Top hash frequency | ${topHash1 ? topHash1[1] : 0}/${r1.results.filter(r => r.ok).length} | ${topHash2 ? topHash2[1] : 0}/${r2.results.filter(r => r.ok).length} | - |\n\n`;

  md += `## 2. Stability Analysis\n\n`;
  const stability1 = topHash1 ? (topHash1[1] / r1.results.filter(r => r.ok).length) * 100 : 0;
  const stability2 = topHash2 ? (topHash2[1] / r2.results.filter(r => r.ok).length) * 100 : 0;
  md += `- **Run 1 stability:** ${stability1.toFixed(1)}% of responses were identical (top hash)\n`;
  md += `- **Run 2 stability:** ${stability2.toFixed(1)}% of responses were identical (top hash)\n`;
  md += `- **Cross-run drift:** ${latencyDrift > 20 ? 'HIGH' : latencyDrift > 10 ? 'MODERATE' : 'LOW'} latency drift (${latencyDrift.toFixed(1)}%)\n\n`;

  md += `## 3. Sample Parsed Response (Run 1)\n\n`;
  md += '```json\n' + JSON.stringify(sample1 ?? { error: 'no parsed sample' }, null, 2) + '\n```\n\n';

  md += `## 4. Sample Parsed Response (Run 2)\n\n`;
  md += '```json\n' + JSON.stringify(sample2 ?? { error: 'no parsed sample' }, null, 2) + '\n```\n\n';

  md += `## 5. Errors (first 5)\n\n`;
  const errors = [...r1.results, ...r2.results].filter(r => !r.ok).slice(0, 5);
  if (errors.length === 0) {
    md += `No errors across ${NUM_CALLS * RUNS} calls.\n\n`;
  } else {
    md += `| Run | Index | Latency | Error |\n|---|---|---|---|\n`;
    for (const e of errors) {
      md += `| ${e.index < NUM_CALLS ? 1 : 2} | ${e.index % NUM_CALLS} | ${e.latencyMs}ms | ${(e.error ?? '').slice(0, 100).replace(/\|/g, '\\|')} |\n`;
    }
    md += '\n';
  }

  md += `## 6. Verdict\n\n`;
  const verdict =
    r1.stats.successRate >= 0.95 &&
    r2.stats.successRate >= 0.95 &&
    r1.stats.parseRate >= 0.9 &&
    r2.stats.parseRate >= 0.9 &&
    Math.abs(latencyDrift) < 25
      ? 'PASS — VLM is stable enough for production integration in Vigie bot.'
      : 'CONDITIONAL — review metrics before production integration.';
  md += `**${verdict}**\n`;

  return md;
}

// ---------- Main ----------
async function main() {
  console.log('VLM Stress Test — Vigie Bot');
  console.log(`Screenshot: ${SCREENSHOT_PATH}`);
  console.log(`Config: ${NUM_CALLS} calls × ${RUNS} runs`);

  const b64 = loadScreenshotAsBase64();
  console.log(`Screenshot base64 length: ${b64.length} chars`);

  const zai = await ZAI.create();

  const runs: RunResult[] = [];
  for (let i = 1; i <= RUNS; i++) {
    const result = await runPass(zai, b64, i);
    runs.push(result);
    fs.writeFileSync(
      path.join(OUTPUT_DIR, `vlm_stress_run${i}.json`),
      JSON.stringify(result, null, 2)
    );
    console.log(`  -> Saved run ${i} to vlm_stress_run${i}.json`);

    if (i < RUNS) {
      console.log('  -> Cooling down 5s before next run...');
      await new Promise(r => setTimeout(r, 5000));
    }
  }

  const report = buildReport(runs);
  fs.writeFileSync(REPORT_PATH, report);
  console.log(`\nReport saved to: ${REPORT_PATH}`);
  console.log('\n--- REPORT PREVIEW ---\n');
  console.log(report.slice(0, 2000));
}

main().catch(err => {
  console.error('FATAL:', err);
  process.exit(1);
});

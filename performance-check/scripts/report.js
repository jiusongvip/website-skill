#!/usr/bin/env node
/**
 * 性能结果解析脚本 —— 兼容 PageSpeed Insights API 与本地 Lighthouse 两种 JSON。
 *
 * 用法：
 *   node scripts/report.js <结果JSON路径>
 * 例：
 *   node scripts/report.js psi-mobile.json
 *   node scripts/report.js lh-mobile.json
 */
const fs = require('fs');

const file = process.argv[2];
if (!file) {
  console.error('用法: node scripts/report.js <psi|lighthouse JSON 路径>');
  process.exit(1);
}

let raw;
try {
  raw = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
  console.error('读取/解析 JSON 失败: ' + e.message);
  process.exit(1);
}

// PSI 输出把 Lighthouse 结果包在 lighthouseResult 下；本地 Lighthouse 直接是顶层
const lr = raw.lighthouseResult || raw;
const cats = lr.categories || {};
const audits = lr.audits || {};
const acat = cats['agentic-browsing']; // 智能体浏览（仅本地 Lighthouse 13.3+ 有）
const disp = (id) => (audits[id] && audits[id].displayValue) || 'n/a';
const score = (name) => {
  const c = cats[name];
  return c && c.score != null ? Math.round(c.score * 100) : 'n/a';
};

console.log('== 性能结果 ==');
console.log(
  JSON.stringify(
    {
      formFactor: lr.configSettings && lr.configSettings.formFactor,
      fetchTime: lr.fetchTime,
      Performance: score('performance'),
      Accessibility: score('accessibility'),
      'Best Practices': score('best-practices'),
      SEO: score('seo'),
      '智能体浏览(仅本地)': acat && acat.score != null ? acat.score : 'n/a',
      LCP: disp('largest-contentful-paint'),
      INP: audits['interaction-to-next-paint'] ? disp('interaction-to-next-paint') : 'n/a(实验室不含)',
      CLS: disp('cumulative-layout-shift'),
      FCP: disp('first-contentful-paint'),
      TBT: disp('total-blocking-time'),
      SI: disp('speed-index'),
      TTFB: disp('server-response-time'),
      'CrUX(页面)': (raw.loadingExperience && raw.loadingExperience.overall_category) || '无',
      'CrUX(源站)': (raw.originLoadingExperience && raw.originLoadingExperience.overall_category) || '无'
    },
    null,
    2
  )
);

// LCP 分解（新版 Lighthouse insight）
const lcpb = audits['lcp-breakdown-insight'];
if (lcpb && lcpb.details && lcpb.details.items && lcpb.details.items[0]) {
  try {
    const parts = lcpb.details.items[0].items.map((x) => x.label + ': ' + Math.round(x.duration) + 'ms');
    console.log('\n== LCP 分解 ==\n' + parts.join('\n'));
  } catch (e) { /* ignore */ }
}

// 优化机会（opportunity 类型，有可节省时间）
console.log('\n== 优化机会（opportunity）==');
let opp = 0;
for (const k in audits) {
  const a = audits[k];
  if (a.details && a.details.type === 'opportunity' && a.details.overallSavingsMs > 0) {
    opp++;
    console.log(a.details.overallSavingsMs.toFixed(0) + 'ms  ' + k + '  ' + a.title);
  }
}
if (!opp) console.log('（无）');

// 体积/其他建议类 insight（score<1 且有展示值）
console.log('\n== 其他建议（*-insight，score<1）==');
let ins = 0;
for (const k of Object.keys(audits)) {
  const a = audits[k];
  if (/-insight$/.test(k) && a.score !== null && a.score < 1 && a.displayValue) {
    ins++;
    console.log((a.score * 100).toFixed(0).padStart(3) + '  ' + k + '  ' + a.displayValue);
  }
}
if (!ins) console.log('（无）');

// 智能体浏览（agentic-browsing，仅本地 Lighthouse 13.3+ 有此类目）
if (acat) {
  console.log('\n== 智能体浏览（agentic-browsing）==');
  console.log('category score: ' + acat.score + ' (' + acat.categoryScoreDisplayMode + ')');
  for (const ref of acat.auditRefs || []) {
    const a = audits[ref.id] || {};
    const sc = a.score == null ? 'n/a ' : a.score === 1 ? 'pass' : a.score === 0 ? 'FAIL' : String(a.score);
    console.log('[' + sc + '] w' + ref.weight + ' ' + ref.id + ' — ' + (a.title || ''));
    if (a.displayValue) console.log('        ' + a.displayValue);
    if (a.details && a.details.items) {
      for (const it of a.details.items) {
        console.log('        - ' + String(it.message || JSON.stringify(it)).slice(0, 160));
      }
    }
  }
}

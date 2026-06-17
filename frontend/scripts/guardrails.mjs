import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(new URL('..', import.meta.url).pathname);
const read = (path) => readFileSync(resolve(root, path), 'utf8');
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const app = read('src/App.tsx');
const engagementGraph = read('src/components/intelligence/EngagementGraph.tsx');
const sphereUtils = read('src/components/sphere/sphereUtils.ts');

expect(
  app.includes('source === "demo-mock"'),
  'App must keep an explicit demo-mock branch for mock-only UI.',
);
expect(
  app.includes('data.attention_duration_seconds != null') && !app.includes('value="8.4s"'),
  'Uploaded Attention Duration must come from data.attention_duration_seconds, not a hardcoded 8.4s value.',
);
expect(
  !app.includes('0.884') && !app.includes('88.4'),
  'App must not render hardcoded 88.4 retention values.',
);
expect(
  !app.includes('3.2}'),
  'App must not render hardcoded 3.2 rewatch values for uploaded analyses.',
);
expect(
  app.includes('data.transcript && data.transcript.segments.length > 0'),
  'TranscriptPanel must only render when transcript segments exist.',
);
expect(
  app.includes('data.top_clips && data.top_clips.length > 0') && app.includes('topClipsSource?.source_type === "unavailable"'),
  'Top clips must not be invented when backend returns no candidates.',
);

expect(
  engagementGraph.includes('retentionScore == null ? "No disponible"') &&
    engagementGraph.includes('rewatchFactor == null ? "No disponible"'),
  'EngagementGraph must show unavailable for null retention/rewatch values.',
);
expect(
  sphereUtils.includes('allowDemoFallback ? DEFAULT_PATH : ""') || !sphereUtils.includes('DEFAULT_PATH'),
  'Uploaded timeline must not use DEFAULT_PATH fallback.',
);
expect(
  sphereUtils.includes('isDemo ?') && sphereUtils.includes(': null') && sphereUtils.includes('data.pacing_score'),
  'Uploaded pacing must not use label-count fallback.',
);
expect(
  sphereUtils.includes('data.hook_score ?? hookFallback') && sphereUtils.includes(') : null;'),
  'Uploaded hook must not use average-virality fallback.',
);

if (failures.length) {
  console.error('Frontend guardrails failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Frontend guardrails passed');

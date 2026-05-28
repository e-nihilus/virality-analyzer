import { Sparkles, Loader2, WifiOff } from "lucide-react";

import { useAnalysis } from "./hooks/useAnalysis";
import { useAnalysisStore } from "./stores/analysisStore";
import SideNav from "./components/layout/SideNav";
import TopAppBar from "./components/layout/TopAppBar";
import BottomNav from "./components/layout/BottomNav";
import VideoPlayer from "./components/video/VideoPlayer";
import VideoUploadPanel from "./components/upload/VideoUploadPanel";
import ViralityScore from "./components/intelligence/ViralityScore";
import EmotionQuadrant from "./components/intelligence/EmotionQuadrant";
import EngagementGraph from "./components/intelligence/EngagementGraph";
import InsightsPanel from "./components/intelligence/InsightsPanel";
import MetricCard from "./components/ui/MetricCard";

export default function App() {
  const { analysis: data, loading, source } = useAnalysis();
  const videoUrl = useAnalysisStore((s) => s.videoUrl);

  if (loading || !data) {
    return (
      <div className="min-h-dvh bg-surface-container-lowest text-on-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} className="text-primary animate-spin" />
          <span className="text-label-sm text-on-surface-variant">
            Loading analysis…
          </span>
        </div>
      </div>
    );
  }

  const peakEntry = data.timeline?.find((e) => e.label === "Pattern disruption");
  const currentTime = peakEntry?.time_seconds ?? 12;
  const duration = data.video?.duration_seconds ?? 45;

  return (
    <div className="min-h-dvh bg-surface-container-lowest text-on-surface antialiased">
      {/* Layout shell */}
      <SideNav />
      <TopAppBar />
      <BottomNav />

      {/* Data source indicator */}
      {source === "local-mock" && (
        <div className="fixed top-16 right-0 lg:right-auto lg:left-20 z-30 m-2">
          <div className="flex items-center gap-1.5 bg-surface-container-high/80 backdrop-blur-md border border-outline-variant/20 rounded-md px-3 py-1.5">
            <WifiOff size={12} className="text-secondary" />
            <span className="text-mono-metric text-secondary">
              Offline — local mock
            </span>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="pt-16 pb-24 lg:pb-0 lg:ml-20 lg:h-[calc(100dvh-64px)] lg:flex lg:overflow-hidden">
        {/* ── Left Column: Intelligence (desktop 45%) ── */}
        <section className="lg:w-[45%] lg:border-r lg:border-outline-variant/10 lg:overflow-y-auto p-4 lg:p-8 space-y-6 lg:space-y-8">
          {/* Header with virality score */}
          <ViralityScore
            score={data.overall_virality_score ?? 0}
            timestamp={`T+00:${currentTime.toFixed(2)}`}
          />

          {/* Mobile: Upload panel or Video player */}
          <div className="lg:hidden">
            {videoUrl ? (
              <VideoPlayer src={videoUrl} currentTime={currentTime} duration={duration} />
            ) : (
              <VideoUploadPanel />
            )}
          </div>

          {/* Emotion Quadrant */}
          <EmotionQuadrant
            valence={peakEntry?.valence}
            arousal={peakEntry?.arousal}
            emotion={data.dominant_emotion}
            intensity={peakEntry?.arousal}
            timestamp={`T+00:${currentTime.toFixed(2)}`}
          />

          {/* Metric Cards */}
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Dominant Emotion"
              value={data.dominant_emotion ?? "—"}
              description="Triggered by abrupt scene transition at 0:12."
              icon={<Sparkles size={20} />}
              color="text-secondary"
            />
            <MetricCard
              label="Attention Duration"
              value="8.4s"
              description="Average focused gaze duration before peak."
              icon={<Sparkles size={20} />}
              color="text-tertiary"
            />
          </div>

          {/* AI Insights */}
          <InsightsPanel insights={data.insights ?? []} />
        </section>

        {/* ── Right Column: Video + Engagement (desktop 55%) ── */}
        <section className="hidden lg:flex lg:w-[55%] flex-col bg-surface-dim">
          {/* Upload panel or Video player */}
          {videoUrl ? (
            <VideoPlayer src={videoUrl} currentTime={currentTime} duration={duration} />
          ) : (
            <VideoUploadPanel className="flex-1 rounded-none border-0 min-h-[300px]" />
          )}

          {/* Engagement Graph */}
          <div className="h-1/3 border-t border-outline-variant/10 bg-surface-container-lowest/80 backdrop-blur-sm overflow-hidden p-6">
            <EngagementGraph
              timeline={data.timeline}
              retentionScore={(data.retention_score ?? 0.884) * 100}
              rewatchFactor={data.rewatch_factor ?? 3.2}
              currentTime={currentTime}
              duration={duration}
            />
          </div>
        </section>

        {/* Mobile: Engagement Graph below insights */}
        <div className="lg:hidden px-4 pb-4">
          <EngagementGraph
            timeline={data.timeline}
            retentionScore={(data.retention_score ?? 0.884) * 100}
            rewatchFactor={data.rewatch_factor ?? 3.2}
            currentTime={currentTime}
            duration={duration}
          />
        </div>
      </main>

      {/* Floating action (desktop only) */}
      <div className="hidden lg:flex fixed bottom-8 right-8 flex-col gap-3 items-end z-30">
        <button className="flex items-center gap-2 bg-surface-container-highest border border-outline-variant/30 px-4 py-3 rounded-full hover:bg-surface-bright transition-all shadow-xl group">
          <Sparkles
            size={18}
            className="text-primary group-hover:rotate-12 transition-transform"
          />
          <span className="font-bold text-label-sm">Analyze Variations</span>
        </button>
      </div>
    </div>
  );
}

import { useRef, useState, useCallback, useEffect } from "react";
import { Play, Pause, SkipForward, Volume2, VolumeX, Maximize, Upload, Sparkles } from "lucide-react";
import TimelineScrubber from "./TimelineScrubber";

interface VideoPlayerProps {
  src?: string | null;
  currentTime?: number;
  duration?: number;
  onSeek?: (time: number) => void;
  onTimeChange?: (time: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onUploadClick?: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VideoPlayer({
  src,
  currentTime: externalTime = 12,
  duration: externalDuration = 45,
  onSeek,
  onTimeChange,
  onPlayingChange,
  onUploadClick,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(externalDuration);

  const hasVideo = !!src;

  useEffect(() => {
    if (!hasVideo) {
      setCurrentTime(externalTime);
      setDuration(externalDuration);
    }
  }, [hasVideo, externalTime, externalDuration]);

  const handleTimeUpdate = useCallback(() => {
    const v = videoRef.current;
    if (v && !v.paused) {
      setCurrentTime(v.currentTime);
      onTimeChange?.(v.currentTime);
    }
  }, [onTimeChange]);

  const handleLoadedMetadata = useCallback(() => {
    const v = videoRef.current;
    if (v) {
      setDuration(v.duration);
      v.play().then(() => {
        setPlaying(true);
        onPlayingChange?.(true);
      }).catch(() => {});
    }
  }, [onPlayingChange]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play();
      setPlaying(true);
      onPlayingChange?.(true);
    } else {
      v.pause();
      setPlaying(false);
      onPlayingChange?.(false);
    }
  }, [onPlayingChange]);

  const toggleMute = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  }, []);

  const progress = duration > 0 ? currentTime / duration : 0;

  const handleSeek = useCallback(
    (p: number) => {
      const time = p * duration;
      if (hasVideo && videoRef.current) {
        videoRef.current.currentTime = time;
        setCurrentTime(time);
      }
      onSeek?.(time);
    },
    [duration, hasVideo, onSeek],
  );

  return (
    <div className="relative flex-1 bg-black flex items-center justify-center group rounded-xl overflow-hidden min-h-[240px] max-h-[55vh]">
      {hasVideo ? (
        <video
          ref={videoRef}
          src={src}
          className="absolute inset-0 w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          playsInline
          loop
          muted
        />
      ) : (
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(45,212,191,0.1)_0%,transparent_70%)]" />
      )}

      {/* Top overlay */}
      <div className="absolute inset-x-0 top-0 p-4 flex items-start justify-between opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="glass-panel rounded-md px-3 py-1.5">
          <span className="text-mono-metric text-on-surface-variant">
            MP4 | 30FPS
          </span>
        </div>
        <div className="flex items-center gap-2">
          {onUploadClick && (
            <button
              onClick={onUploadClick}
              className="glass-panel rounded-md p-2 text-on-surface-variant hover:text-primary transition-colors"
              title="Upload video"
            >
              <Upload size={16} />
            </button>
          )}
          <button className="glass-panel rounded-md p-2 text-on-surface-variant hover:text-on-surface transition-colors">
            <Maximize size={16} />
          </button>
        </div>
      </div>

      {/* Bottom overlay with scrim */}
      <div className="absolute inset-x-0 bottom-0 scrim-bottom pt-16 pb-4 px-4 space-y-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <TimelineScrubber
          progress={progress}
          onSeek={handleSeek}
        />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={hasVideo ? togglePlay : undefined}
              className="text-on-surface hover:text-primary transition-colors"
            >
              {playing ? (
                <Pause size={20} fill="currentColor" />
              ) : (
                <Play size={20} fill="currentColor" />
              )}
            </button>
            <button className="text-on-surface-variant hover:text-on-surface transition-colors">
              <SkipForward size={18} />
            </button>
            <button
              onClick={hasVideo ? toggleMute : undefined}
              className="text-on-surface-variant hover:text-on-surface transition-colors"
            >
              {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>
            <span className="text-mono-metric text-on-surface-variant">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-secondary">
            <Sparkles size={14} />
            <span className="text-mono-metric">AI Enhancement Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}

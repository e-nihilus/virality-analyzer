import { useCallback, useRef, useState } from "react";
import { Upload, Film, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import clsx from "clsx";
import { useVideoUpload } from "../../hooks/useVideoUpload";

interface VideoUploadPanelProps {
  className?: string;
}

export default function VideoUploadPanel({ className }: VideoUploadPanelProps) {
  const { status, progress, error, upload, reset } = useVideoUpload();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (file) upload(file);
    },
    [upload],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      handleFile(file);
    },
    [handleFile],
  );

  if (status === "done") {
    return (
      <div className="glass-panel rounded-xl p-6 flex flex-col items-center gap-3 text-center">
        <CheckCircle2 size={32} className="text-tertiary" />
        <p className="text-body-md text-on-surface">Analysis complete</p>
        <button
          onClick={reset}
          className="text-label-sm text-primary hover:text-primary-fixed transition-colors"
        >
          Upload another video
        </button>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="glass-panel rounded-xl p-6 flex flex-col items-center gap-3 text-center">
        <AlertCircle size={32} className="text-error" />
        <p className="text-body-md text-error">{error}</p>
        <button
          onClick={reset}
          className="text-label-sm text-primary hover:text-primary-fixed transition-colors"
        >
          Try again
        </button>
      </div>
    );
  }

  if (status === "uploading" || status === "processing") {
    const isProcessing = status === "processing";
    return (
      <div className="glass-panel rounded-xl p-6 flex flex-col items-center gap-4">
        <div className="relative">
          <Loader2
            size={28}
            className={clsx(
              "animate-spin",
              isProcessing ? "text-tertiary" : "text-primary",
            )}
          />
          {isProcessing && (
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-tertiary pulse-glow" />
          )}
        </div>
        <p className="text-body-md text-on-surface-variant">
          {isProcessing ? "AI analyzing your video…" : "Uploading…"}
        </p>
        {isProcessing && (
          <p className="text-mono-metric text-on-surface-variant/50">
            Extracting frames · Building timeline · Scoring
          </p>
        )}
        <div className="w-full h-1 bg-surface-container-highest rounded-full overflow-hidden">
          <div
            className={clsx(
              "h-full rounded-full transition-all duration-700",
              isProcessing ? "bg-tertiary" : "bg-primary",
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  // idle — dropzone
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={clsx(
        "glass-panel rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer",
        "border-2 border-dashed transition-colors",
        dragOver
          ? "border-primary bg-primary/5"
          : "border-outline-variant/30 hover:border-primary/50",
        className,
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.webm,.avi,.mkv"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      <div className="w-14 h-14 rounded-xl bg-surface-container-highest flex items-center justify-center">
        {dragOver ? (
          <Film size={24} className="text-primary" />
        ) : (
          <Upload size={24} className="text-on-surface-variant" />
        )}
      </div>

      <div className="text-center">
        <p className="text-body-md text-on-surface">
          {dragOver ? "Drop to analyze" : "Drop a video or click to upload"}
        </p>
        <p className="text-mono-metric text-on-surface-variant/60 mt-1">
          MP4, MOV, WebM, AVI, MKV — Max 200 MB
        </p>
      </div>
    </div>
  );
}

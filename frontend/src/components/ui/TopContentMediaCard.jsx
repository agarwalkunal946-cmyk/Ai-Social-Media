import { useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, Maximize2, Play, X } from "lucide-react";

function getYouTubeEmbedUrl(videoId, autoPlay = true) {
  if (!videoId) return "";
  return `https://www.youtube.com/embed/${videoId}?rel=0${autoPlay ? "&autoplay=1" : ""}`;
}

function getThumbnail(item) {
  if (item.thumbnail) return item.thumbnail;
  if (item.player_type === "youtube" && item.video_id) {
    return `https://img.youtube.com/vi/${item.video_id}/hqdefault.jpg`;
  }
  if (item.player_type === "x" && item.media_url) return item.media_url;
  return null;
}

function isPlayable(item) {
  if (item.player_type === "youtube") return Boolean(item.video_id);
  if (item.player_type === "instagram") return Boolean(item.media_url);
  if (item.player_type === "x") return Boolean(item.media_url);
  return false;
}

function MediaPlayer({ item, autoPlay = true }) {
  if (item.player_type === "youtube" && item.video_id) {
    return (
      <div className="aspect-video overflow-hidden rounded-2xl bg-black">
        <iframe
          src={getYouTubeEmbedUrl(item.video_id, autoPlay)}
          title={item.title || "YouTube player"}
          className="h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
    );
  }

  if (item.player_type === "instagram" && item.media_url) {
    return (
      <div className="overflow-hidden rounded-2xl bg-black">
        <video
          src={item.media_url}
          poster={getThumbnail(item) || undefined}
          controls
          playsInline
          autoPlay={autoPlay}
          className="aspect-video h-full w-full bg-black object-contain"
        />
      </div>
    );
  }

  if (item.player_type === "x" && item.media_url) {
    return (
      <div className="overflow-hidden rounded-2xl bg-black">
        <video
          src={item.media_url}
          poster={getThumbnail(item) || undefined}
          controls
          playsInline
          autoPlay={autoPlay}
          className="aspect-video h-full w-full bg-black object-contain"
        />
      </div>
    );
  }

  return null;
}

function PlayerModal({ item, open, onClose }) {
  if (typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      {open && item && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[70] bg-black/80 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-[80] flex items-center justify-center p-4 md:p-6">
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.98 }}
              className="w-full max-w-5xl overflow-hidden rounded-3xl border border-white/[0.08] bg-slate-950/95 shadow-2xl backdrop-blur-2xl"
            >
              <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-6 py-5">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-neon/70">Top content player</p>
                  <h2 className="mt-2 line-clamp-2 font-display text-2xl font-bold text-white">{item.title}</h2>
                  {item.creator && <p className="mt-2 text-sm text-slate-400">{item.creator}</p>}
                </div>
                <button type="button" onClick={onClose} className="text-slate-500 transition hover:text-white">
                  <X size={18} />
                </button>
              </div>
              <div className="p-6">
                <MediaPlayer item={item} autoPlay />
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
    ,
    document.body
  );
}

export function TopContentMediaCard({ item, compact = false }) {
  const [showPlayerModal, setShowPlayerModal] = useState(false);
  const playable = isPlayable(item);
  const thumbnail = getThumbnail(item);

  return (
    <>
      <div className={`flex h-full flex-col rounded-2xl border border-white/[0.05] bg-white/[0.03] ${compact ? "p-3" : "p-4"}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {item.platform}
          </span>
          <span className="text-xs font-semibold text-neon">{item.metric}</span>
        </div>

        <div className={`mt-3 overflow-hidden rounded-2xl border border-white/[0.05] bg-slate-950/70 ${compact ? "aspect-[16/9]" : "aspect-video"}`}>
          {thumbnail ? (
            <button
              type="button"
              onClick={() => playable && setShowPlayerModal(true)}
              className={`relative h-full w-full ${playable ? "cursor-pointer" : "cursor-default"}`}
            >
              <img src={thumbnail} alt={item.title || "Content preview"} className="h-full w-full object-cover" />
              {playable && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                  <span
                    className="flex h-11 w-11 items-center justify-center rounded-full bg-black/75 shadow-lg ring-1 ring-white/15"
                    style={{ color: "#ffffff" }}
                  >
                    <Play size={18} className="ml-0.5" fill="currentColor" />
                  </span>
                </div>
              )}
            </button>
          ) : (
            <div className="flex h-full items-center justify-center px-4 text-center text-sm text-slate-500">
              No preview available
            </div>
          )}
        </div>

        <div className="mt-3 flex flex-1 flex-col">
          <div>
            <h3 className={`font-display font-bold text-white ${compact ? "line-clamp-2 text-sm" : "line-clamp-2 text-base"}`}>
              {item.title}
            </h3>
            {item.creator && <p className="mt-1 truncate text-xs text-slate-500">{item.creator}</p>}
            {item.insight && <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-slate-400">{item.insight}</p>}
          </div>

          <div className="mt-auto flex flex-wrap gap-2 pt-3">
            {playable && (
              <button
                type="button"
                onClick={() => setShowPlayerModal(true)}
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/[0.06] hover:text-white"
              >
                <Maximize2 size={14} />
                Big view
              </button>
            )}
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/[0.06] hover:text-white"
              >
                <ExternalLink size={14} />
                Open source
              </a>
            )}
          </div>
        </div>
      </div>
      <PlayerModal item={item} open={showPlayerModal} onClose={() => setShowPlayerModal(false)} />
    </>
  );
}

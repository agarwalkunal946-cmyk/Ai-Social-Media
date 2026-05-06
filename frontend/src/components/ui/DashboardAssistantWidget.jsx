import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, MessageSquareText, Send, Sparkles, X } from "lucide-react";

import { Button } from "./Button";
import { TopContentMediaCard } from "./TopContentMediaCard";

function AssistantResponse({ item, onAsk }) {
  return (
    <div className={`rounded-3xl p-4 ${item.role === "assistant" ? "bg-white/[0.03]" : "bg-neon/[0.06]"}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        {item.role === "assistant" ? "Assistant" : "You"}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-white">{item.text}</p>

      {!!item.bullets?.length && (
        <div className="mt-3 space-y-2">
          {item.bullets.map((bullet) => (
            <p key={bullet} className="text-xs leading-relaxed text-slate-400">{bullet}</p>
          ))}
        </div>
      )}

      {!!item.statCards?.length && (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {item.statCards.map((card) => (
            <div key={`${card.label}-${card.value}`} className="rounded-2xl border border-white/[0.06] bg-black/20 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{card.label}</p>
              <p className="mt-2 font-display text-base font-bold text-white">{card.value}</p>
              {card.detail && <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{card.detail}</p>}
            </div>
          ))}
        </div>
      )}

      {!!item.mediaItems?.length && (
        <div className="mt-4 grid gap-3">
          {item.mediaItems.slice(0, 3).map((mediaItem) => (
            <TopContentMediaCard key={`${item.role}-${mediaItem.id}`} item={mediaItem} compact />
          ))}
        </div>
      )}

      {!!item.followUp?.length && (
        <div className="mt-4 flex flex-wrap gap-2">
          {item.followUp.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => onAsk(question)}
              className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function DashboardAssistantWidget({
  chatbotConfig,
  chatHistory,
  chatInput,
  setChatInput,
  chatbotMutation,
  sendMessage,
  open,
  setOpen,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (chatHistory.length) {
      setOpen(true);
    }
  }, [chatHistory.length]);

  useEffect(() => {
    if (!scrollRef.current) {
      return;
    }
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [chatHistory, chatbotMutation.isPending, open]);

  const askQuestion = async (question) => {
    if (!question) return;
    setOpen(true);
    await sendMessage(question);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="fixed bottom-6 right-6 z-[65] flex h-16 w-16 items-center justify-center rounded-full border border-neon/20 bg-slate-950/90 text-neon shadow-2xl backdrop-blur-2xl transition hover:scale-[1.02] hover:text-white"
        aria-label={open ? "Close assistant" : "Open assistant"}
      >
        <div className="absolute inset-0 rounded-full bg-neon/10" />
        <div className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full bg-emerald-400 ring-2 ring-slate-950" />
        <Bot size={24} className="relative z-10" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            className="fixed bottom-24 right-3 z-[64] w-[min(30rem,calc(100vw-1.5rem))] overflow-hidden rounded-[2rem] border border-white/[0.08] bg-slate-950/95 shadow-2xl backdrop-blur-2xl sm:right-6"
          >
            <div className="border-b border-white/[0.06] px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-neon/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-neon">
                    <Sparkles size={12} />
                    AI Analytics
                  </div>
                  <h2 className="mt-3 font-display text-xl font-bold text-white">{chatbotConfig?.title || "AI social media analytics assistant"}</h2>
                  <p className="mt-2 text-xs leading-relaxed text-slate-400">
                    {chatbotConfig?.greeting || "Ask about dashboard values, public search analytics, connected accounts, trends, formulas, models, sentiment, alerts, or recommendations."}
                  </p>
                </div>
                <button type="button" onClick={() => setOpen(false)} className="text-slate-500 transition hover:text-white">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div ref={scrollRef} className="max-h-[60vh] overflow-y-auto px-5 py-4">
              {chatHistory.length === 0 && (
                <div className="rounded-3xl border border-white/[0.06] bg-white/[0.03] p-4">
                  <div className="flex items-center gap-2 text-neon">
                    <MessageSquareText size={16} />
                    <p className="text-sm font-medium">Ask about analytics, app features, formulas, or public platform search</p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {(chatbotConfig?.starter_questions || []).map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => askQuestion(question)}
                        className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-3">
                {chatHistory.map((item, index) => (
                  <AssistantResponse key={`${item.role}-${index}`} item={item} onAsk={askQuestion} />
                ))}
              </div>

              {chatbotMutation.isPending && (
                <div className="mt-3 rounded-3xl bg-white/[0.03] p-4 text-sm text-slate-400">
                  Reviewing dashboard metrics and live public platform analytics...
                </div>
              )}
            </div>

            <div className="border-t border-white/[0.06] px-5 py-4">
              <div className="mb-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                {(chatbotConfig?.scope || ["Dashboard values", "Connected account analytics", "Public platform search"]).map((item) => (
                  <span key={item} className="rounded-full bg-white/[0.03] px-2.5 py-1">{item}</span>
                ))}
              </div>
              <div className="flex gap-3">
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      askQuestion(chatInput);
                    }
                  }}
                  placeholder={chatbotConfig?.input_placeholder || 'Ask about analytics or the app, for example: "Search MrBeast on YouTube"'}
                  className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
                />
                <Button className="gap-2" onClick={() => askQuestion(chatInput)} disabled={chatbotMutation.isPending}>
                  <Send size={14} />
                  Ask
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

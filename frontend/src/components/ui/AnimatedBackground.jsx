export function AnimatedBackground() {
  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    dur: `${5 + Math.random() * 8}s`,
    delay: `${-Math.random() * 8}s`,
    size: Math.random() > 0.7 ? 3 : 2,
    opacity: 0.15 + Math.random() * 0.25,
  }));

  return (
    <>
      {/* Mesh gradient blobs */}
      <div className="mesh-bg" aria-hidden="true" />

      {/* Floating particles */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden" aria-hidden="true">
        {particles.map((p) => (
          <div
            key={p.id}
            className="particle"
            style={{
              left: p.left,
              top: p.top,
              "--dur": p.dur,
              "--delay": p.delay,
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: p.opacity,
              animationDelay: p.delay,
            }}
          />
        ))}
      </div>
    </>
  );
}

export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 80 80" fill="none" className={className} aria-hidden="true">
      <rect width="80" height="80" rx="16" fill="#FF4F00" />
      <circle cx="24" cy="22" r="7" fill="white" />
      <circle cx="56" cy="40" r="7" fill="white" />
      <circle cx="24" cy="58" r="7" fill="white" />
      <line x1="28" y1="26" x2="52" y2="37" stroke="white" strokeWidth="4" strokeLinecap="round" />
      <line x1="28" y1="54" x2="52" y2="43" stroke="white" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

export function LogoFull({ className = "h-7" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark className="h-[1em] w-[1em] text-[28px]" />
      <span className="heading text-[18px] leading-none text-ink">Black Box</span>
    </span>
  );
}

export function LogoFullWhite({ className = "h-7" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark className="h-[1em] w-[1em] text-[28px]" />
      <span className="heading text-[18px] leading-none text-white">Black Box</span>
    </span>
  );
}

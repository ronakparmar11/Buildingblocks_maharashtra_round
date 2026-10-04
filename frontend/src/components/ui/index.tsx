import {
  AlertCircle,
  Check,
  ChevronDown,
  Copy,
  LoaderCircle,
  Search,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { t } from "../../lib/vocab";

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "orange" | "ink" | "secondary" | "quiet";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}) {
  const variants = {
    orange: "bg-orange text-white border-orange hover:bg-[#e54600] active:bg-[#cc3f00]",
    ink: "bg-ink-btn text-white border-ink-btn hover:bg-ink-btn-hover active:bg-ink-btn-active",
    secondary: "bg-panel text-ink border-rule hover:bg-rule-soft active:bg-rule",
    quiet: "border-transparent bg-transparent text-advisory hover:bg-rule-soft/60 active:bg-rule-soft",
  };
  const sizes = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-sm",
    lg: "h-11 px-5 text-md",
  };
  return (
    <button
      className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-control border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
export function OutcomeChip({ outcome }: { outcome: string }) {
  const style =
    outcome === "pass"
      ? "bg-normal-tint text-normal"
      : outcome === "fail"
        ? "bg-warning-tint-deep text-warning"
        : "bg-rule-soft text-graphite";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-chip px-2.5 py-1 text-xs font-medium ${style}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {outcome === "pass" ? "Passed" : outcome === "fail" ? "Failed" : "Error"}
    </span>
  );
}
export function RunTypeLabel({ origin }: { origin: string }) {
  const labels: Record<string, string> = {
    fault: "Injected failure",
    organic: "Natural failure",
    clean: `Clean ${t("run")}`,
    replay: "Replay",
    repair: "Fix attempt",
    live: `Live ${t("run")}`,
  };
  return (
    <span className="text-xs text-graphite">{labels[origin] ?? origin}</span>
  );
}
export function StepKey({
  value,
  copy = false,
}: {
  value: string;
  copy?: boolean;
}) {
  const className = `inline-block max-w-full truncate rounded-chip bg-rule-soft px-2 py-1 font-mono text-xs text-ink${copy ? " cursor-pointer transition-colors hover:bg-rule" : ""}`;
  if (!copy)
    return <span title={value} className={className}>{value}</span>;
  return (
    <button
      type="button"
      title="Copy step key"
      onClick={() => navigator.clipboard.writeText(value)}
      className={className}
    >
      {value}
      <Copy className="ml-1 inline h-3 w-3" />
    </button>
  );
}
export function ScoreMeter({ score }: { score: number }) {
  return (
    <span
      className="inline-flex items-center gap-1"
      aria-label={`Score ${score.toFixed(2)}`}
    >
      <span className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((part) => (
          <span
            key={part}
            className={`h-3 w-1 ${score * 5 >= part ? "bg-caution" : "bg-rule"}`}
          />
        ))}
      </span>
      <span className="font-mono text-xs">{score.toFixed(2)}</span>
    </span>
  );
}
export const StatChip = ({ children }: { children: ReactNode }) => (
  <span className="rounded-chip border border-rule bg-panel px-2.5 py-1 font-mono text-xs">
    {children}
  </span>
);
export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
}) {
  return (
    <div className="flex border-b border-rule">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={`px-3 py-2 text-sm transition-colors ${active === tab ? "border-b-2 border-ink text-ink" : "text-graphite hover:text-ink"}`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
export function Drawer({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const panel = useRef<HTMLElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement as HTMLElement;
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab" && panel.current) {
        const focusable = [
          ...panel.current.querySelectorAll<HTMLElement>(
            'button,a,input,select,textarea,[tabindex]:not([tabindex="-1"])',
          ),
        ];
        if (!focusable.length) return;
        const first = focusable[0],
          last = focusable.at(-1)!;
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    requestAnimationFrame(() =>
      panel.current?.querySelector<HTMLElement>("button")?.focus(),
    );
    return () => {
      document.removeEventListener("keydown", key);
      returnFocus.current?.focus();
    };
  }, [open, onClose]);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (open) requestAnimationFrame(() => setVisible(true));
    else setVisible(false);
  }, [open]);
  if (!open) return null;
  return (
    <div className={`fixed inset-0 z-50 transition-colors duration-150 ${visible ? "bg-black/20" : "bg-black/0"}`} onMouseDown={onClose}>
      <aside
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
        className={`ml-auto h-full w-full max-w-[480px] overflow-auto border-l border-rule bg-panel p-6 shadow-popover transition-transform duration-200 ${visible ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="mb-6 flex items-center justify-between">
          <h2 className="heading text-lg">{title}</h2>
          <button aria-label="Close" onClick={onClose}>
            <X />
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
export function Popover({
  trigger,
  children,
  closeOnContentClick = false,
}: {
  trigger: ReactNode;
  children: ReactNode;
  closeOnContentClick?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const onClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);
  return (
    <span ref={ref} className="relative inline-block">
      <span onClick={() => setOpen(!open)}>{trigger}</span>
      {open && (
        <span
          onClick={() => closeOnContentClick && setOpen(false)}
          className="absolute right-0 top-full z-30 mt-2 w-72 rounded-panel border border-rule bg-panel p-4 text-sm shadow-popover"
        >
          {children}
        </span>
      )}
    </span>
  );
}
export function Tooltip({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const [show, setShow] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const id = useId();
  const enter = () => { timer.current = setTimeout(() => setShow(true), 300); };
  const leave = () => { clearTimeout(timer.current); setShow(false); };
  return (
    <span className="relative inline-flex" onMouseEnter={enter} onMouseLeave={leave} onFocus={enter} onBlur={leave} aria-describedby={show ? id : undefined}>
      {children}
      {show && (
        <span id={id} role="tooltip" className="absolute bottom-full left-1/2 z-40 mb-2 -translate-x-1/2 whitespace-nowrap rounded-control bg-ink-btn px-2.5 py-1 text-xs text-white shadow-popover">
          {label}
        </span>
      )}
    </span>
  );
}
export function Toast({
  message,
  onClose,
}: {
  message: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3500);
    return () => clearTimeout(timer);
  }, [onClose]);
  return (
    <div className="fixed bottom-6 right-6 z-50 rounded-control bg-ink-btn px-4 py-3 text-white shadow-popover">
      {message}
    </div>
  );
}
export function JsonViewer({ value }: { value: unknown }) {
  return (
    <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-control border border-rule bg-paper p-3 font-mono text-xs">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
export function JsonEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string, valid: boolean) => void;
}) {
  const [error, setError] = useState("");
  const change = (next: string) => {
    try {
      JSON.parse(next);
      setError("");
      onChange(next, true);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Invalid JSON";
      setError(message);
      onChange(next, false);
    }
  };
  return (
    <div>
      <textarea
        value={value}
        onChange={(event) => change(event.target.value)}
        rows={14}
        className="w-full resize-y rounded-control border border-rule bg-paper p-3 font-mono text-xs"
      />
      <p
        className={`mt-2 flex items-center gap-1 text-xs ${error ? "text-warning" : "text-normal"}`}
      >
        {error ? (
          <AlertCircle className="h-3 w-3" />
        ) : (
          <Check className="h-3 w-3" />
        )}
        {error || "Valid JSON"}
      </p>
    </div>
  );
}
export function PassageCard({
  passage,
}: {
  passage: { title: string; text: string; score: number; status?: string; updated_at?: string };
}) {
  return (
    <article className="rounded-node border border-rule bg-panel p-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="heading">{passage.title}</h4>
            {passage.status === "archived" && <span className="rounded-chip bg-caution-tint px-2 py-0.5 text-xs">Archived</span>}
          </div>
          {passage.updated_at && <p className="mt-1 text-xs text-graphite">Updated {new Date(passage.updated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>}
        </div>
        <span className="font-mono text-xs">{passage.score.toFixed(2)}</span>
      </div>
      <p className="mt-2 line-clamp-4 text-sm text-graphite">{passage.text}</p>
    </article>
  );
}
export function WordDiff({ parts }: { parts: string[] }) {
  return (
    <p className="font-mono text-xs">
      {parts.map((part, index) => (
        <span
          key={index}
          className={
            part[0] === "+"
              ? "bg-normal-tint text-normal"
              : part[0] === "-"
                ? "bg-warning-tint-deep text-warning line-through"
                : ""
          }
        >
          {part.slice(1)}
        </span>
      ))}
    </p>
  );
}
export const Skeleton = ({
  className = "h-5 w-full",
}: {
  className?: string;
}) => (
  <div className={`animate-pulse rounded-control bg-rule-soft ${className}`} />
);
export function EmptyState({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="grid min-h-48 place-items-center text-center">
      <div>
        <p className="text-graphite">{title}</p>
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  );
}
export function ErrorState({
  message = `Couldn't load this ${t("run")}. The server returned 500. Check that the API is running on port 8000, then reload.`,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="grid min-h-48 place-items-center text-center">
      <div>
        <AlertCircle className="mx-auto mb-3 text-warning" />
        <p className="max-w-xl">{message}</p>
        {onRetry && (
          <Button className="mt-4" onClick={onRetry}>
            Reload
          </Button>
        )}
      </div>
    </div>
  );
}
export function FilterPill({
  label,
  value,
  onClear,
  children,
}: {
  label: string;
  value?: string;
  onClear?: () => void;
  children?: ReactNode;
}) {
  return (
    <button className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-chip border border-rule bg-panel px-3 text-sm transition-colors hover:border-advisory hover:text-ink">
      {label}
      {value && `: ${value}`}
      {children ??
        (value ? (
          <X
            onClick={(event) => {
              event.stopPropagation();
              onClear?.();
            }}
            className="h-3 w-3"
          />
        ) : (
          <ChevronDown className="h-3 w-3" />
        ))}
    </button>
  );
}
export function Select({
  value,
  onChange,
  options,
  placeholder = "Select…",
  className: cls = "",
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const listId = useId();
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", esc); };
  }, [open]);
  const selected = options.find((o) => o.value === value);
  return (
    <div ref={ref} className={`relative inline-block ${cls}`}>
      <button
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={ariaLabel}
        onClick={() => setOpen(!open)}
        className={`flex h-9 w-full items-center gap-2 rounded-chip border px-3 text-sm transition-colors ${value ? "border-advisory bg-panel text-ink" : "border-rule bg-panel text-graphite"} hover:border-advisory`}
      >
        <span className="min-w-0 truncate">{selected?.label ?? placeholder}</span>
        <ChevronDown className={`ml-auto h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul id={listId} role="listbox" className="absolute left-0 top-full z-40 mt-1 max-h-60 w-full min-w-[180px] overflow-auto rounded-panel border border-rule bg-panel py-1 shadow-popover">
          {options.map((o) => (
            <li
              key={o.value}
              role="option"
              aria-selected={o.value === value}
              onClick={() => { onChange(o.value); setOpen(false); }}
              className={`cursor-pointer px-3 py-2 text-sm transition-colors ${o.value === value ? "bg-rule-soft font-medium text-ink" : "text-graphite hover:bg-rule-soft/60 hover:text-ink"}`}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
export function Combobox({
  value,
  onChange,
  options,
  placeholder = "Search…",
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const filtered = options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()));
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", esc); };
  }, [open]);
  const pick = useCallback((v: string) => { onChange(v); setOpen(false); setQuery(""); }, [onChange]);
  const selected = options.find((o) => o.value === value);
  return (
    <div ref={ref} className="relative block">
      <Search className="absolute left-3 top-2.5 h-4 w-4 text-graphite" />
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        placeholder={selected?.label ?? placeholder}
        value={open ? query : selected?.label ?? ""}
        onFocus={() => { setOpen(true); setQuery(""); }}
        onChange={(e) => { setQuery(e.target.value); if (!open) setOpen(true); }}
        className="h-10 w-full rounded-control border border-rule bg-panel pl-9 pr-8 text-sm transition-colors hover:border-advisory focus:border-advisory"
      />
      <ChevronDown className={`absolute right-3 top-3 h-4 w-4 text-graphite transition-transform ${open ? "rotate-180" : ""}`} />
      {open && (
        <ul id={listId} role="listbox" className="absolute left-0 top-full z-40 mt-1 max-h-60 w-full overflow-auto rounded-panel border border-rule bg-panel py-1 shadow-popover">
          {filtered.length === 0 && <li className="px-3 py-2 text-sm text-graphite">No results</li>}
          {filtered.map((o) => (
            <li
              key={o.value}
              role="option"
              aria-selected={o.value === value}
              onClick={() => pick(o.value)}
              className={`cursor-pointer px-3 py-2 text-sm transition-colors ${o.value === value ? "bg-rule-soft font-medium text-ink" : "text-graphite hover:bg-rule-soft/60 hover:text-ink"}`}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
export function SegmentedControl({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="inline-flex rounded-control border border-rule bg-panel p-0.5">
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          className={`rounded-[4px] px-3 py-1.5 text-xs transition-colors ${value === option ? "bg-ink-btn text-white" : "text-graphite hover:text-ink"}`}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
export const KpiRow = ({
  items,
}: {
  items: { value: string; label: string }[];
}) => (
  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
    {items.map((item, i) => (
      <div
        key={item.label}
        className={`relative overflow-hidden rounded-panel border border-rule bg-panel p-4 sm:p-5 ${i === 0 ? "col-span-2 sm:col-span-1" : ""}`}
      >
        <span className="absolute left-0 top-0 h-full w-[3px] rounded-r bg-orange opacity-0 transition-opacity group-hover:opacity-100" style={{ opacity: i === 0 ? 1 : 0 }} />
        <strong className="block font-mono text-2xl text-ink">{item.value}</strong>
        <p className="mt-1.5 text-sm leading-snug text-graphite">{item.label}</p>
      </div>
    ))}
  </div>
);

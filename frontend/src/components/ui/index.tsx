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
    orange: "bg-orange text-white border-orange",
    ink: "bg-ink text-white border-ink",
    secondary: "bg-panel text-ink border-rule",
    quiet: "border-transparent bg-transparent text-advisory",
  };
  const sizes = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-sm",
    lg: "h-11 px-5 text-md",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-control border font-medium disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
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
        ? "bg-[#F9DEE2] text-warning"
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
  const className = "inline-block max-w-full truncate rounded-chip bg-rule-soft px-2 py-1 font-mono text-xs text-ink";
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
          className={`px-3 py-2 text-sm ${active === tab ? "border-b-2 border-ink text-ink" : "text-graphite"}`}
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
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-ink/20" onMouseDown={onClose}>
      <aside
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
        className="ml-auto h-full w-full max-w-[480px] overflow-auto border-l border-rule bg-panel p-6 shadow-popover"
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
  return (
    <span className="relative inline-block">
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
export const Tooltip = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => <span title={label}>{children}</span>;
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
    <div className="fixed bottom-6 right-6 z-50 rounded-control bg-ink px-4 py-3 text-white shadow-popover">
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
                ? "bg-[#F9DEE2] text-warning line-through"
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
    <button className="inline-flex h-9 items-center gap-2 rounded-chip border border-rule bg-panel px-3 text-sm">
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
  const id = useId();
  return (
    <label htmlFor={id} className="relative block">
      <Search className="absolute left-3 top-2.5 h-4 w-4 text-graphite" />
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full appearance-none rounded-control border border-rule bg-panel pl-9 pr-8"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
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
          className={`rounded-[4px] px-3 py-1.5 text-xs ${value === option ? "bg-ink text-white" : "text-graphite"}`}
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
  <div className="grid divide-x divide-rule border-y border-rule bg-panel sm:grid-cols-5">
    {items.map((item) => (
      <div key={item.label} className="p-5">
        <strong className="font-mono text-2xl">{item.value}</strong>
        <p className="mt-1 max-w-36 text-sm text-graphite">{item.label}</p>
      </div>
    ))}
  </div>
);

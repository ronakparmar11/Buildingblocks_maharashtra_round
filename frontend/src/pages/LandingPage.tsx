import {
  ArrowRight,
  Check,
  Gauge,
  GitCompareArrows,
  Play,
  Radar,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";

const capabilities = [
  {
    icon: Radar,
    number: "01",
    title: "Record the whole run",
    text: "Capture prompts, retrievals, tool calls, model outputs, latency, tokens, and dependencies as one inspectable trace.",
  },
  {
    icon: Sparkles,
    number: "02",
    title: "Find the responsible step",
    text: "Rank likely causes with evidence, instead of asking teams to read logs and guess where the answer diverged.",
  },
  {
    icon: GitCompareArrows,
    number: "03",
    title: "Replay only what changed",
    text: "Reuse trusted upstream work, rerun the smallest repair, and compare the result against the original failure.",
  },
];

export default function LandingPage() {
  return (
    <main className="bg-paper text-ink">
      <header className="absolute inset-x-0 top-0 z-20 h-16 border-b border-white/20 text-white">
        <div className="mx-auto flex h-full max-w-[1440px] items-center px-5 sm:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label="Black Box home">
            <span className="h-4 w-4 bg-orange" />
            <span className="heading text-lg">Black Box</span>
          </Link>
          <nav className="ml-auto hidden items-center gap-7 text-sm text-white/75 sm:flex">
            <a href="#how-it-works" className="hover:text-white">How it works</a>
            <a href="#proof" className="hover:text-white">Product</a>
          </nav>
          <Link to="/signin" className="ml-5 inline-flex h-9 items-center gap-2 rounded-control border border-white/30 px-4 text-sm font-medium text-white hover:bg-white/10">
            Sign in <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <section
        className="relative flex min-h-[calc(100svh-48px)] items-end overflow-hidden bg-ink bg-cover bg-center pt-28 text-white"
        style={{ backgroundImage: "url('/golden-demo-preview.png')" }}
      >
        <div className="absolute inset-0 bg-ink/90" />
        <div className="absolute inset-y-0 right-0 hidden w-[42%] border-l border-white/10 bg-ink/35 lg:block" />
        <div className="relative mx-auto grid w-full max-w-[1440px] gap-8 px-5 pb-10 sm:px-8 sm:pb-20 lg:grid-cols-[minmax(0,0.9fr)_minmax(360px,0.55fr)] lg:items-end lg:gap-12 lg:pb-24">
          <div className="max-w-4xl">
            <p className="mb-6 flex items-center gap-3 font-mono text-xs uppercase text-orange">
              <span className="h-px w-8 bg-orange" /> AI failure intelligence
            </p>
            <h1 className="heading text-[52px] leading-[56px] sm:text-[72px] sm:leading-[76px]">Black Box</h1>
            <p className="heading mt-4 max-w-3xl text-2xl leading-8 text-white sm:text-3xl sm:leading-10">
              The flight recorder for AI agents.
            </p>
            <p className="mt-6 max-w-2xl text-md leading-7 text-white/70">
              See every decision behind a wrong answer, isolate the step that caused it, and verify the smallest possible repair without rerunning the entire agent.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/signin" className="inline-flex h-12 items-center gap-2 rounded-control bg-orange px-5 text-sm font-medium text-white">
                <Play className="h-4 w-4" /> Open the judge demo
              </Link>
              <a href="#how-it-works" className="inline-flex h-12 items-center gap-2 rounded-control border border-white/30 px-5 text-sm font-medium text-white">
                See how it works <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>

          <div className="grid grid-cols-3 border border-white/20 bg-ink/75 lg:grid-cols-1">
            {[
              ["12", "steps recorded"],
              ["94%", "culprit confidence"],
              ["1", "step rerun to repair"],
            ].map(([value, label]) => (
              <div key={label} className="border-r border-white/20 px-3 py-3 last:border-r-0 sm:px-5 sm:py-4 lg:border-b lg:border-r-0 lg:last:border-b-0">
                <p className="font-mono text-2xl text-white">{value}</p>
                <p className="mt-1 text-xs text-white/55">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="bg-orange px-5 py-4 text-white">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3">
          <p className="heading text-lg">A wrong answer is not one event. It is a chain of decisions.</p>
          <span className="font-mono text-xs uppercase">Observe · Diagnose · Repair · Verify</span>
        </div>
      </div>

      <section id="how-it-works" className="border-b border-rule bg-panel px-5 py-20 sm:px-8 sm:py-28">
        <div className="mx-auto max-w-[1440px]">
          <div className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr]">
            <div>
              <p className="font-mono text-xs uppercase text-advisory">From incident to evidence</p>
              <h2 className="heading mt-4 max-w-md text-3xl leading-[44px]">Stop debugging AI systems from the final answer backward.</h2>
            </div>
            <p className="max-w-2xl self-end text-lg leading-8 text-graphite">
              Traditional monitoring tells you that an agent failed. Black Box preserves the execution path that explains why, then turns that evidence into a targeted repair workflow.
            </p>
          </div>

          <div className="mt-14 grid border-y border-rule lg:grid-cols-3">
            {capabilities.map(({ icon: Icon, number, title, text }, index) => (
              <article key={title} className={`py-7 lg:px-7 lg:py-9 ${index < capabilities.length - 1 ? "border-b border-rule lg:border-b-0 lg:border-r" : ""} ${index === 0 ? "lg:pl-0" : ""}`}>
                <div className="flex items-center justify-between">
                  <Icon className="h-5 w-5 text-orange" />
                  <span className="font-mono text-xs text-ghost">{number}</span>
                </div>
                <h3 className="heading mt-8 text-xl">{title}</h3>
                <p className="mt-3 max-w-sm text-sm leading-6 text-graphite">{text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="proof" className="bg-paper px-5 py-20 sm:px-8 sm:py-28">
        <div className="mx-auto max-w-[1440px]">
          <div className="grid items-end gap-8 lg:grid-cols-[1fr_0.8fr]">
            <div>
              <p className="font-mono text-xs uppercase text-advisory">Evidence, not another dashboard</p>
              <h2 className="heading mt-4 max-w-3xl text-3xl leading-[44px]">One saved investigation tells the complete story.</h2>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm text-graphite">
              <p className="flex items-center gap-2"><Check className="h-4 w-4 text-normal" /> Works without LLM quota</p>
              <p className="flex items-center gap-2"><Gauge className="h-4 w-4 text-advisory" /> Measures repair cost</p>
              <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-normal" /> Keeps source evidence</p>
              <p className="flex items-center gap-2"><GitCompareArrows className="h-4 w-4 text-advisory" /> Compares every change</p>
            </div>
          </div>

          <div className="mt-12 overflow-hidden border border-rule bg-panel shadow-popover">
            <div className="flex items-center gap-2 border-b border-rule px-4 py-3">
              <span className="h-2 w-2 rounded-full bg-warning" />
              <span className="h-2 w-2 rounded-full bg-caution" />
              <span className="h-2 w-2 rounded-full bg-normal" />
              <span className="ml-3 font-mono text-[11px] text-graphite">Saved Golden Demo · no provider calls</span>
            </div>
            <img src="/golden-demo-preview.png" alt="Black Box Golden Demo showing a failed AI answer, its recorded execution trace, culprit diagnosis, and verified repair" className="block h-auto w-full" />
          </div>
        </div>
      </section>

      <section className="border-t border-rule bg-ink px-5 py-16 text-white sm:px-8 sm:py-20">
        <div className="mx-auto flex max-w-[1440px] flex-col items-start justify-between gap-8 sm:flex-row sm:items-end">
          <div>
            <p className="font-mono text-xs uppercase text-orange">Prepared judge flow</p>
            <h2 className="heading mt-4 max-w-2xl text-3xl leading-[44px]">Watch one failure become one verified fix.</h2>
            <p className="mt-4 max-w-xl text-sm text-white/60">The account is prefilled and the investigation is recorded, so the demonstration stays reliable on stage.</p>
          </div>
          <Link to="/signin" className="inline-flex h-12 shrink-0 items-center gap-2 rounded-control bg-orange px-5 text-sm font-medium text-white">
            Enter Black Box <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-ink px-5 py-6 text-white/45 sm:px-8">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between text-xs">
          <span>Black Box</span>
          <span>AI failure intelligence</span>
        </div>
      </footer>
    </main>
  );
}
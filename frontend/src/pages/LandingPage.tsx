import {
  ArrowRight,
  Check,
  ChevronRight,
  Gauge,
  GitCompareArrows,
  Play,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { lazy, useState, Suspense } from "react";
import { Link } from "react-router-dom";
import { LogoMark } from "../components/Logo";

const DitherWave = lazy(() => import("../components/DitherWave"));
const RisingLines = lazy(() => import("../components/RisingLines"));

const capabilities = [
  {
    icon: Radar,
    number: "01",
    title: "Record every step",
    text: "Prompts, retrievals, tool calls, model outputs, latency, tokens and dependencies — captured as one inspectable trace.",
  },
  {
    icon: Sparkles,
    number: "02",
    title: "Find the responsible step",
    text: "A trained ranker surfaces the likely cause with evidence, instead of making teams read logs and guess.",
  },
  {
    icon: GitCompareArrows,
    number: "03",
    title: "Replay only what changed",
    text: "Reuse trusted upstream work, rerun the smallest repair, and compare the result against the original failure.",
  },
  {
    icon: Zap,
    number: "04",
    title: "Verify automatically",
    text: "Run the fix across every affected conversation and measure cost, accuracy and token savings before you deploy.",
  },
];

const stats = [
  { value: "12", label: "steps recorded per run" },
  { value: "94%", label: "culprit confidence" },
  { value: "1", label: "step rerun to repair" },
  { value: "<2ms", label: "diagnosis latency" },
];

function FlipCard({ icon: Icon, number, title, text }: { icon: typeof Radar; number: string; title: string; text: string }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <article
      onClick={() => setFlipped((f) => !f)}
      className="cursor-pointer [perspective:800px]"
    >
      <div
        className={`relative h-full transition-transform duration-500 [transform-style:preserve-3d] ${flipped ? "[transform:rotateY(180deg)]" : ""}`}
      >
        {/* Front */}
        <div className="rounded-panel border border-white/10 bg-white/[0.03] p-6 [backface-visibility:hidden]">
          <div className="flex items-center justify-between">
            <span className="grid h-10 w-10 place-items-center rounded-control bg-orange/10 text-orange">
              <Icon className="h-5 w-5" />
            </span>
            <span className="font-mono text-xs text-white/25">{number}</span>
          </div>
          <h3 className="heading mt-5 text-lg text-white">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-white/50">{text}</p>
        </div>
        {/* Back */}
        <div className="absolute inset-0 rounded-panel bg-orange p-6 [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <div className="flex items-center justify-between">
            <span className="grid h-10 w-10 place-items-center rounded-control bg-indigo-600/20 text-indigo-200">
              <Icon className="h-5 w-5" />
            </span>
            <span className="font-mono text-xs text-indigo-300">{number}</span>
          </div>
          <h3 className="heading mt-5 text-lg text-indigo-950">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-indigo-900">{text}</p>
        </div>
      </div>
    </article>
  );
}

export default function LandingPage() {
  return (
    <main className="bg-ink text-white selection:bg-orange/30">
      {/* ─── Nav ─── */}
      <header className="fixed inset-x-0 top-0 z-30">
        <div className="mx-auto mt-3 flex h-12 max-w-3xl items-center rounded-chip border border-white/10 bg-ink/60 px-5 backdrop-blur-xl sm:mx-8 md:mx-auto">
          <Link to="/" className="flex items-center gap-2" aria-label="Black Box home">
            <LogoMark className="h-6 w-6" />
            <span className="heading text-sm">Black Box</span>
          </Link>
          <nav className="ml-auto hidden items-center gap-6 text-xs text-white/60 sm:flex">
            <a href="#how-it-works" className="transition-colors hover:text-white">How it works</a>
            <a href="#product" className="transition-colors hover:text-white">Product</a>
            <a href="#demo" className="transition-colors hover:text-white">Demo</a>
          </nav>
          <Link
            to="/signin"
            className="ml-5 inline-flex h-7 items-center gap-1.5 rounded-chip bg-orange px-3.5 text-xs font-medium text-white transition-colors hover:bg-[#e54600]"
          >
            Sign in <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </header>

      {/* ─── Hero ─── */}
      <section className="relative overflow-hidden pt-16">
        <Suspense fallback={null}>
          <DitherWave
            className="absolute inset-0 h-full w-full opacity-60"
            primaryColor="#FF4F00"
            secondaryColor="#FF8C42"
            tertiaryColor="#14202B"
            speed={0.8}
            intensity={1.2}
            scale={7}
          />
        </Suspense>

        <div className="relative mx-auto max-w-[1440px] px-5 pb-20 pt-28 sm:px-8 sm:pb-32 sm:pt-36">
          <div className="mx-auto max-w-4xl text-center">
            <h1 className="heading text-[44px] leading-[1.1] sm:text-[64px] lg:text-[76px] [text-shadow:0_2px_24px_rgba(0,0,0,.5)]">
              Know why your AI failed.{" "}
              <span className="text-orange">Fix only what broke.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-white/70 sm:text-xl [text-shadow:0_1px_8px_rgba(0,0,0,.6)]">
              Black Box records every decision behind a wrong answer, isolates the responsible step, and verifies the smallest possible repair without rerunning the entire agent.
            </p>
            <div className="mt-10 flex flex-wrap justify-center gap-4">
              <Link
                to="/signin"
                className="inline-flex h-12 items-center gap-2 rounded-control bg-orange px-6 text-sm font-medium text-white shadow-[0_0_24px_rgba(255,79,0,.25)] transition-all hover:bg-[#e54600] hover:shadow-[0_0_32px_rgba(255,79,0,.35)]"
              >
                <Play className="h-4 w-4" /> Open the judge demo
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex h-12 items-center gap-2 rounded-control border border-white/30 bg-ink/50 px-6 text-sm font-medium text-white backdrop-blur-sm transition-colors hover:border-white/50 hover:bg-ink/70"
              >
                See how it works <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Stats row */}
          <div className="mx-auto mt-20 grid max-w-3xl grid-cols-2 gap-px overflow-hidden rounded-panel border border-white/10 bg-white/10 sm:grid-cols-4">
            {stats.map(({ value, label }) => (
              <div key={label} className="bg-ink/80 px-5 py-5 text-center backdrop-blur-md">
                <p className="font-mono text-2xl font-bold text-white">{value}</p>
                <p className="mt-1 text-xs text-white/50">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Marquee bar ─── */}
      <div className="overflow-hidden border-y border-white/10 bg-orange py-4">
        <div className="flex animate-[marquee_20s_linear_infinite] gap-12 whitespace-nowrap">
          {[0, 1].map((copy) => (
            <span key={copy} className="flex shrink-0 items-center gap-12" aria-hidden={copy === 1 || undefined}>
              {["A wrong answer is not one event. It is a chain of decisions.", "Observe", "Diagnose", "Repair", "Verify"].map((text, i) => (
                <span key={`${copy}-${i}`} className="flex items-center gap-12">
                  <span className={i === 0 ? "heading text-lg text-white" : "font-mono text-xs uppercase tracking-widest text-white/80"}>{text}</span>
                  <span className="text-white/30">|</span>
                </span>
              ))}
            </span>
          ))}
        </div>
      </div>

      {/* ─── How it works ─── */}
      <section id="how-it-works" className="bg-[#0d1117] px-5 py-24 sm:px-8 sm:py-32">
        <div className="mx-auto max-w-[1440px]">
          <div className="grid gap-8 lg:grid-cols-[0.65fr_1.35fr]">
            <div>
              <p className="inline-flex items-center gap-2 font-mono text-xs uppercase text-advisory">
                <Search className="h-3.5 w-3.5" /> From incident to evidence
              </p>
              <h2 className="heading mt-5 max-w-md text-3xl leading-[1.2] text-white sm:text-[40px]">
                Stop debugging AI from the final answer backward.
              </h2>
            </div>
            <p className="max-w-2xl self-end text-lg leading-8 text-white/55">
              Traditional monitoring tells you that an agent failed. Black Box preserves the execution path that explains why, then turns that evidence into a targeted repair workflow.
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map(({ icon: Icon, number, title, text }) => (
              <FlipCard key={title} icon={Icon} number={number} title={title} text={text} />
            ))}
          </div>
        </div>
      </section>

      {/* ─── Product screenshot ─── */}
      <section id="product" className="bg-ink px-5 py-24 sm:px-8 sm:py-32">
        <div className="mx-auto max-w-[1440px]">
          <div className="grid items-end gap-8 lg:grid-cols-[1fr_0.8fr]">
            <div>
              <p className="inline-flex items-center gap-2 font-mono text-xs uppercase text-advisory">
                <ShieldCheck className="h-3.5 w-3.5" /> Evidence, not another dashboard
              </p>
              <h2 className="heading mt-5 max-w-3xl text-3xl leading-[1.2] text-white sm:text-[40px]">
                One saved investigation tells the complete story.
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm text-white/55">
              <p className="flex items-center gap-2"><Check className="h-4 w-4 text-normal" /> Works without LLM quota</p>
              <p className="flex items-center gap-2"><Gauge className="h-4 w-4 text-advisory" /> Measures repair cost</p>
              <p className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-normal" /> Keeps source evidence</p>
              <p className="flex items-center gap-2"><GitCompareArrows className="h-4 w-4 text-advisory" /> Compares every change</p>
            </div>
          </div>

          <div className="mt-14 overflow-hidden rounded-panel border border-white/10 bg-[#0d1117] shadow-[0_16px_48px_rgba(0,0,0,.4)]">
            <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-caution/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-normal/70" />
              <span className="ml-4 font-mono text-[11px] text-white/35">Saved Golden Demo · no provider calls</span>
            </div>
            <img
              src="/golden-demo-preview.png"
              alt="Black Box Golden Demo showing a failed AI answer, its recorded execution trace, culprit diagnosis, and verified repair"
              className="block h-auto w-full"
            />
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section id="demo" className="relative overflow-hidden border-t border-white/10 bg-[#0d1117] px-5 py-24 sm:px-8 sm:py-28">
        <Suspense fallback={null}>
          <RisingLines
            className="absolute inset-0 h-full w-full"
            color="#FF4F00"
            haloColor="#FF8C42"
            horizonColor="#FF4F00"
            particleCount={60}
            beamCount={5}
            riseSpeed={0.35}
          />
        </Suspense>
        <div className="relative mx-auto max-w-[1440px]">
          <div className="mx-auto max-w-2xl text-center">
            <p className="font-mono text-xs uppercase text-orange">Prepared judge flow</p>
            <h2 className="heading mt-5 text-3xl leading-[1.2] text-white sm:text-[40px] [text-shadow:0_2px_16px_rgba(0,0,0,.5)]">
              Watch one failure become one verified fix.
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-white/60 [text-shadow:0_1px_6px_rgba(0,0,0,.5)]">
              The account is prefilled and the investigation is recorded, so the demonstration stays reliable on stage. No live LLM quota is consumed.
            </p>
            <Link
              to="/signin"
              className="relative mt-8 inline-flex h-12 items-center gap-2 rounded-control bg-orange px-6 text-sm font-medium text-white shadow-[0_0_24px_rgba(255,79,0,.25)] transition-all hover:bg-[#e54600] hover:shadow-[0_0_32px_rgba(255,79,0,.35)]"
            >
              Enter Black Box <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-white/10 bg-ink px-5 py-7 sm:px-8">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between">
          <span className="flex items-center gap-2">
            <LogoMark className="h-5 w-5" />
            <span className="text-xs text-white/40">Black Box</span>
          </span>
          <span className="text-xs text-white/30">AI failure intelligence</span>
        </div>
      </footer>
    </main>
  );
}

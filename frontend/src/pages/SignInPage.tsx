import { ArrowLeft, ArrowRight, Eye, EyeOff, Loader2, LockKeyhole, Mail, Sparkles } from "lucide-react";
import { lazy, Suspense, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiPost, ApiError } from "../api/client";
import type { SessionResponse } from "../api/types";
import { LogoMark } from "../components/Logo";

const DitherWave = lazy(() => import("../components/DitherWave"));

const DEMO_EMAIL = "blackbox@gmail.com";
const DEMO_PASSWORD = "blackbox123";

const STEPS = [
  { label: "Observe", detail: "Record every decision" },
  { label: "Diagnose", detail: "Isolate the faulty step" },
  { label: "Repair", detail: "Replay the smallest fix" },
  { label: "Verify", detail: "Prove it with evidence" },
];

const inputClass =
  "h-11 w-full rounded-control border border-rule bg-white pl-10 text-sm text-ink shadow-sm transition-colors placeholder:text-ghost hover:border-[#5B6873]/50 focus:border-orange focus:outline-none focus:ring-4 focus:ring-[#FF4F00]/15";

export default function SignInPage({ onSignedIn }: { onSignedIn: (session: SessionResponse) => void }) {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      onSignedIn(await apiPost<SessionResponse>("/auth/login", { email, password }));
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 401 ? "Invalid email or password." : "Sign in is unavailable. Check that the API is running.");
    } finally {
      setSubmitting(false);
    }
  };

  const fillDemo = () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setError("");
  };

  return (
    <main className="min-h-screen bg-ink text-white selection:bg-[#FF4F00]/30">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.25fr)_minmax(460px,0.75fr)]">
        <section className="relative flex flex-col overflow-hidden px-6 py-7 sm:px-10 lg:min-h-screen lg:px-16 lg:py-10">
          <Suspense fallback={null}>
            <DitherWave
              className="absolute inset-0 h-full w-full opacity-40"
              primaryColor="#FF4F00"
              secondaryColor="#FF8C42"
              tertiaryColor="#14202B"
              speed={0.6}
              intensity={1}
              scale={7}
            />
          </Suspense>
          <div className="absolute inset-0 bg-gradient-to-t from-ink via-[#14202B]/40 to-[#14202B]/70" />

          <div className="relative flex items-center gap-3">
            <Link to="/" className="flex items-center gap-3" aria-label="Back to Black Box home">
              <LogoMark className="h-8 w-8" />
              <span className="heading text-lg">Black Box</span>
            </Link>
            <Link to="/" className="ml-auto inline-flex items-center gap-1.5 rounded-chip border border-white/15 bg-[#14202B]/50 px-3 py-1 text-xs text-white/70 backdrop-blur transition-colors hover:border-white/40 hover:text-white">
              <ArrowLeft className="h-3 w-3" /> Home
            </Link>
          </div>

          <div className="relative my-auto max-w-2xl py-14 lg:py-20">
            <p className="mb-5 inline-flex items-center gap-2 rounded-chip border border-[#FF4F00]/30 bg-[#FF4F00]/10 px-3 py-1 font-mono text-xs uppercase text-orange">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-orange" /> AI failure intelligence
            </p>
            <h1 className="heading text-3xl leading-tight sm:text-[52px] sm:leading-[58px] [text-shadow:0_2px_24px_rgba(0,0,0,.5)]">
              Know why your AI failed. <span className="text-orange">Fix only what broke.</span>
            </h1>
            <p className="mt-6 max-w-xl text-md leading-7 text-white/70">
              Black Box records every decision, finds the responsible step, and replays the smallest possible fix with measurable evidence.
            </p>
          </div>

          <ol className="relative hidden gap-px overflow-hidden rounded-panel border border-white/10 bg-white/10 sm:grid sm:grid-cols-4">
            {STEPS.map(({ label, detail }, index) => (
              <li key={label} className="bg-[#14202B]/80 px-4 py-4 backdrop-blur-md">
                <span className="font-mono text-xs text-orange">0{index + 1}</span>
                <p className="mt-1 text-sm font-medium">{label}</p>
                <p className="mt-0.5 text-xs text-white/50">{detail}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex items-center bg-paper px-6 py-12 text-ink sm:px-12 lg:rounded-l-[28px] lg:px-16">
          <form onSubmit={submit} className="mx-auto w-full max-w-sm">
            <p className="font-mono text-xs uppercase text-orange">Welcome back</p>
            <h2 className="heading mt-3 text-2xl">Sign in to Black Box</h2>
            <p className="mt-2 text-sm text-graphite">Monitor, diagnose, and repair AI failures with evidence-based investigations.</p>

            <button
              type="button"
              onClick={fillDemo}
              className="mt-7 flex w-full items-center gap-3 rounded-panel border border-dashed border-[#FF4F00]/40 bg-[#FFE4D6]/50 px-4 py-3 text-left transition-colors hover:border-orange hover:bg-orange-tint"
            >
              <Sparkles className="h-4 w-4 shrink-0 text-orange" />
              <span className="min-w-0 text-xs text-graphite">
                <span className="block font-medium text-ink">Demo account</span>
                <span className="font-mono">{DEMO_EMAIL} · {DEMO_PASSWORD}</span>
              </span>
            </button>

            <label className="mt-6 block text-sm font-medium" htmlFor="email">Email</label>
            <div className="relative mt-2">
              <Mail className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-graphite" />
              <input id="email" type="email" required autoComplete="username" placeholder="you@company.com" value={email} onChange={(event) => setEmail(event.target.value)} className={`${inputClass} pr-3`} />
            </div>

            <label className="mt-5 block text-sm font-medium" htmlFor="password">Password</label>
            <div className="relative mt-2">
              <LockKeyhole className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-graphite" />
              <input id="password" type={showPassword ? "text" : "password"} required autoComplete="current-password" placeholder="••••••••" value={password} onChange={(event) => setPassword(event.target.value)} className={`${inputClass} pr-11`} />
              <button type="button" title={showPassword ? "Hide password" : "Show password"} aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-control text-graphite transition-colors hover:bg-rule-soft hover:text-ink">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {error && <p role="alert" className="mt-5 rounded-control border border-[#C8223A]/30 bg-warning-tint px-3 py-2 text-sm text-warning">{error}</p>}

            <button type="submit" disabled={submitting} className="group mt-7 inline-flex h-11 w-full items-center justify-center gap-2 rounded-control bg-orange px-5 text-sm font-medium text-white shadow-[0_0_24px_rgba(255,79,0,.25)] transition-all hover:bg-[#e54600] hover:shadow-[0_0_32px_rgba(255,79,0,.35)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#FF4F00]/30 disabled:cursor-wait disabled:opacity-70">
              {submitting ? <><Loader2 className="h-4 w-4 animate-spin" /> Signing in…</> : <>Sign in <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" /></>}
            </button>

            <p className="mt-8 text-center text-xs text-graphite">
              Protected workspace · Sessions are scoped to your account
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}

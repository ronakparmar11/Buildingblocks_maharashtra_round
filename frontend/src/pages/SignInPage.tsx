import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { apiPost, ApiError } from "../api/client";
import type { SessionResponse } from "../api/types";

const DEMO_EMAIL = "blackbox@gmail.com";
const DEMO_PASSWORD = "blackbox123";

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
      setError(cause instanceof ApiError && cause.status === 401 ? "The demo email or password is incorrect." : "Sign in is unavailable. Check that the API is running.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-ink text-white">
      <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.35fr)_minmax(420px,0.65fr)]">
        <section className="relative flex min-h-[54vh] flex-col overflow-hidden border-b border-white/15 px-6 py-7 sm:px-10 lg:min-h-screen lg:border-b-0 lg:border-r lg:px-16 lg:py-10">
          <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(255,255,255,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.08)_1px,transparent_1px)] [background-size:40px_40px]" />
          <div className="relative flex items-center gap-3">
            <span className="h-4 w-4 bg-orange" />
            <span className="heading text-lg">Black Box</span>
            <span className="ml-auto rounded-chip border border-white/20 px-3 py-1 text-xs text-white/70">Judge build</span>
          </div>

          <div className="relative my-auto max-w-3xl py-12 lg:py-20">
            <p className="mb-5 font-mono text-xs uppercase text-orange">AI failure intelligence</p>
            <h1 className="heading max-w-2xl text-3xl leading-tight sm:text-[48px] sm:leading-[54px]">
              Know why your AI failed. Fix only what broke.
            </h1>
            <p className="mt-6 max-w-xl text-md leading-7 text-white/70">
              Black Box records every decision, finds the responsible step, and replays the smallest possible fix with measurable evidence.
            </p>
          </div>

          <div className="relative grid gap-0 border border-white/15 bg-black/15 sm:grid-cols-4">
            {["Observe", "Diagnose", "Repair", "Verify"].map((label, index) => (
              <div key={label} className="flex items-center gap-3 border-b border-white/15 px-4 py-4 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full font-mono text-xs ${index === 2 ? "bg-orange text-white" : "border border-white/25 text-white/70"}`}>{index + 1}</span>
                <span className="text-sm font-medium">{label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="flex items-center bg-panel px-6 py-12 text-ink sm:px-12 lg:px-14">
          <form onSubmit={submit} className="mx-auto w-full max-w-md">
            <div className="mb-9 flex h-12 w-12 items-center justify-center rounded-control bg-orange-tint text-orange">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <p className="font-mono text-xs uppercase text-advisory">Prepared demonstration</p>
            <h2 className="heading mt-3 text-2xl">Enter the investigation room</h2>
            <p className="mt-3 text-sm text-graphite">The judge account is prefilled. Sign in to open the saved, quota-free failure investigation.</p>

            <label className="mt-8 block text-sm font-medium" htmlFor="email">Email</label>
            <div className="relative mt-2">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-graphite" />
              <input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} className="h-10 w-full rounded-control border border-rule bg-white pl-10 pr-3 text-sm" />
            </div>

            <label className="mt-5 block text-sm font-medium" htmlFor="password">Password</label>
            <div className="relative mt-2">
              <LockKeyhole className="absolute left-3 top-3 h-4 w-4 text-graphite" />
              <input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="h-10 w-full rounded-control border border-rule bg-white pl-10 pr-10 text-sm" />
              <button type="button" title={showPassword ? "Hide password" : "Show password"} aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-2 grid h-6 w-6 place-items-center text-graphite">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {error && <p role="alert" className="mt-4 border-l-2 border-warning pl-3 text-sm text-warning">{error}</p>}
            <button type="submit" disabled={submitting} className="mt-7 inline-flex h-11 w-full items-center justify-center gap-2 rounded-control bg-orange px-5 text-sm font-medium text-white disabled:opacity-60">
              {submitting ? "Opening demo..." : "Open judge demo"}
              {!submitting && <ArrowRight className="h-4 w-4" />}
            </button>
            <p className="mt-4 text-center text-xs text-graphite">Recorded evidence only. No live LLM quota is used.</p>
          </form>
        </section>
      </div>
    </main>
  );
}
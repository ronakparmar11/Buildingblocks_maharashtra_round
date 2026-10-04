import {
  Bot, Headphones, Mic, MicOff, RotateCcw, Send, Sparkles, Volume2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useVoiceAnswer } from "../api/hooks";
import { Button, ErrorState } from "../components/ui";
import { useWorkspace, workspaceDetails } from "../context/workspace";

type SpeechEvent = { results: ArrayLike<{ 0: { transcript: string } }> };
type SpeechRecognizer = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognizerConstructor = new () => SpeechRecognizer;
type SpeechWindow = typeof window & {
  SpeechRecognition?: SpeechRecognizerConstructor;
  webkitSpeechRecognition?: SpeechRecognizerConstructor;
};

const examples = [
  "I bought a bedsheet in the Diwali sale. How long can I return it?",
  "How long does a COD refund take after I share my bank details?",
  "Can I exchange the same order twice for a different colour?",
];

function speak(text: string) {
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = 0.94;
  window.speechSynthesis.speak(utterance);
}

function Waveform({ active, answered }: { active: boolean; answered: boolean }) {
  const bars = [18, 34, 50, 26, 60, 42, 22, 54, 31, 58, 28, 45, 20, 38, 52, 30];
  return <div className="flex h-20 items-center justify-center gap-1.5" aria-hidden="true">
    {bars.map((height, index) => <span
      key={index}
      className={`w-1.5 rounded-full ${answered ? "bg-normal" : "bg-orange"} ${active ? "animate-pulse" : "opacity-35"}`}
      style={{ height, animationDelay: `${index * 45}ms` }}
    />)}
  </div>;
}

export default function VoiceLabPage() {
  const { workspace } = useWorkspace();
  const voice = useVoiceAnswer();
  const [transcript, setTranscript] = useState(examples[0]);
  const [listening, setListening] = useState(false);
  const recognition = useRef<SpeechRecognizer | null>(null);
  const speechWindow = window as SpeechWindow;
  const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;

  useEffect(() => () => {
    recognition.current?.stop();
    window.speechSynthesis.cancel();
  }, []);

  const askAssistant = (spoken = transcript) => {
    const cleanTranscript = spoken.trim();
    if (!cleanTranscript) return;
    voice.mutate(
      { transcript: cleanTranscript },
      { onSuccess: (result) => speak(result.answer) },
    );
  };

  const toggleListening = () => {
    if (listening) {
      recognition.current?.stop();
      setListening(false);
      return;
    }
    if (!Recognition) return;
    const instance = new Recognition();
    instance.continuous = false;
    instance.interimResults = false;
    instance.lang = "en-IN";
    instance.onresult = (event) => {
      const spoken = event.results[0][0].transcript;
      setTranscript(spoken);
      askAssistant(spoken);
    };
    instance.onend = () => setListening(false);
    instance.onerror = () => setListening(false);
    recognition.current = instance;
    voice.reset();
    setListening(true);
    instance.start();
  };

  const reset = () => {
    recognition.current?.stop();
    window.speechSynthesis.cancel();
    setListening(false);
    setTranscript(examples[0]);
    voice.reset();
  };

  return <div className="min-h-[calc(100vh-56px)] bg-paper">
    <header className="border-b border-rule bg-panel px-4 py-7 sm:px-6">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-start justify-between gap-5">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-advisory">
            <Headphones className="h-4 w-4" /> AI voice assistant
            <span className="rounded-chip bg-advisory-tint px-2 py-0.5 text-advisory">Mock Nimbu help center</span>
          </div>
          <h1 className="heading mt-3 text-2xl sm:text-3xl">Ask naturally. Get a spoken answer.</h1>
          <p className="mt-2 max-w-2xl text-sm text-graphite">{workspaceDetails[workspace].name} · English (India)</p>
        </div>
        <Button onClick={reset}><RotateCcw className="h-4 w-4" /> Reset</Button>
      </div>
    </header>

    <main className="mx-auto grid max-w-[1280px] gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[0.72fr_1.28fr]">
      <section className="overflow-hidden rounded-panel border border-rule bg-ink text-white">
        <div className="p-6 sm:p-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className={`grid h-11 w-11 place-items-center rounded-full ${listening ? "bg-orange" : "bg-white/10"}`}><Mic className="h-5 w-5" /></span>
              <div><p className="text-sm font-semibold">Voice channel</p><p className="text-xs text-white/55">en-IN · browser speech</p></div>
            </div>
            <span className="flex items-center gap-2 text-xs text-white/70"><span className={`h-2 w-2 rounded-full ${voice.isPending || listening ? "animate-pulse bg-orange" : "bg-normal"}`} />{listening ? "Listening" : voice.isPending ? "Thinking" : "Ready"}</span>
          </div>

          <div className="my-10"><Waveform active={listening || voice.isPending} answered={Boolean(voice.data)} /></div>

          <button
            onClick={toggleListening}
            disabled={!Recognition || voice.isPending}
            title={Recognition ? "Start voice question" : "Speech recognition is unavailable in this browser"}
            className={`flex h-14 w-full items-center justify-center gap-2 rounded-control font-semibold transition-colors ${listening ? "bg-orange text-white" : "bg-white text-ink hover:bg-white/90"} disabled:cursor-not-allowed disabled:opacity-45`}
          >
            {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            {listening ? "Stop listening" : "Ask with voice"}
          </button>
        </div>
        <div className="border-t border-white/10 px-6 py-4 text-xs text-white/55">Your transcript is answered using mock help-center content. No production customer data is used.</div>
      </section>

      <div className="space-y-6">
        <section className="rounded-panel border border-rule bg-panel p-5 sm:p-7">
          <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-orange" /><h2 className="heading text-lg">Customer question</h2></div>
          <textarea
            value={transcript}
            onChange={(event) => { setTranscript(event.target.value); voice.reset(); }}
            rows={4}
            maxLength={1000}
            className="mt-4 w-full resize-none rounded-node border border-rule bg-paper px-4 py-3 leading-6 outline-none transition-colors focus:border-advisory"
            placeholder="Ask about returns, refunds, delivery, payments, or warranty…"
          />
          <div className="mt-3 flex flex-wrap gap-2">{examples.map((example, index) => <button key={example} onClick={() => { setTranscript(example); voice.reset(); }} className="rounded-chip border border-rule px-3 py-1.5 text-left text-xs text-graphite hover:border-advisory hover:text-advisory">Example {index + 1}</button>)}</div>
          <div className="mt-5 flex justify-end"><Button variant="orange" size="lg" loading={voice.isPending} disabled={!transcript.trim()} onClick={() => askAssistant()}><Send className="h-4 w-4" /> Ask assistant</Button></div>
        </section>

        {voice.isError && <ErrorState onRetry={() => askAssistant()} />}

        {voice.data && <section className="overflow-hidden rounded-panel border border-normal/30 bg-panel">
          <div className="p-5 sm:p-7">
            <div className="flex items-center gap-2 text-normal"><Bot className="h-5 w-5" /><span className="text-xs font-semibold uppercase">Assistant answered</span></div>
            <p className="mt-4 text-lg leading-8 text-ink">{voice.data.answer}</p>
            <button onClick={() => speak(voice.data!.answer)} className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-normal"><Volume2 className="h-4 w-4" /> Play answer again</button>
          </div>
          <div className="grid border-t border-rule bg-normal-tint sm:grid-cols-2">
            <div className="border-b border-rule px-5 py-4 sm:border-b-0 sm:border-r"><p className="text-[11px] text-graphite">Latency</p><p className="mt-1 font-mono text-xs font-medium">{voice.data.latency_ms} ms</p></div>
            <div className="px-5 py-4"><p className="text-[11px] text-graphite">Tokens</p><p className="mt-1 font-mono text-xs font-medium">{voice.data.tokens_in} in · {voice.data.tokens_out} out</p></div>
          </div>
          <div className="border-t border-rule px-5 py-4"><p className="text-[11px] uppercase text-graphite">Mock articles used</p><div className="mt-2 flex flex-wrap gap-2">{voice.data.sources.map((source) => <span key={source} className="rounded-chip bg-paper px-2.5 py-1 text-xs text-graphite">{source}</span>)}</div></div>
        </section>}
      </div>
    </main>
  </div>;
}

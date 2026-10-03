import { useState } from "react";
import {
  Button,
  Combobox,
  EmptyState,
  ErrorState,
  FilterPill,
  JsonEditor,
  JsonViewer,
  KpiRow,
  OutcomeChip,
  PassageCard,
  RunTypeLabel,
  ScoreMeter,
  SegmentedControl,
  Skeleton,
  StatChip,
  StepKey,
  Tabs,
  WordDiff,
} from "../components/ui";
const colors = [
  ["paper", "bg-paper"], ["panel", "bg-panel"], ["ink", "bg-ink"],
  ["graphite", "bg-graphite"], ["rule", "bg-rule"], ["rule-soft", "bg-rule-soft"],
  ["orange", "bg-orange"], ["orange-tint", "bg-orange-tint"], ["warning", "bg-warning"],
  ["caution", "bg-caution"], ["caution-tint", "bg-caution-tint"], ["normal", "bg-normal"],
  ["normal-tint", "bg-normal-tint"], ["advisory", "bg-advisory"], ["ghost", "bg-ghost"],
];
const typeSizes = [["xs","text-xs"],["sm","text-sm"],["md","text-md"],["lg","text-lg"],["xl","text-xl"],["2xl","text-2xl"],["3xl","text-3xl"]];
export default function Styleguide() {
  const [tab, setTab] = useState("Why");
  const [segment, setSegment] = useState("Seen");
  const [json, setJson] = useState('{"answer":"yes"}');
  return (
    <div className="mx-auto max-w-[1200px] space-y-10 px-6 py-8">
      <div>
        <h1 className="heading text-xl">Styleguide</h1>
        <p className="mt-1 text-graphite">
          Shared patterns for the investigation board.
        </p>
      </div>
      <section>
        <h2 className="heading mb-4 text-lg">Color</h2>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
          {colors.map(([name, className]) => (
            <div key={name}>
              <div className={`h-16 rounded-node border border-rule ${className}`} />
              <p className="mt-1 font-mono text-xs">{name}</p>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2 className="heading mb-4 text-lg">Type</h2>
        {typeSizes.map(([name, className]) => (
          <p key={name} className={className}>
            Black Box <span className="font-mono">r_8f2c</span>
          </p>
        ))}
      </section>
      <section className="space-y-5">
        <h2 className="heading text-lg">Components</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="orange">Find the cause</Button>
          <Button variant="ink">Try fixes</Button>
          <Button>Replay from this step</Button>
          <Button variant="quiet">Quiet action</Button>
          <Button disabled>Disabled</Button>
          <Button loading>Loading</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <OutcomeChip outcome="pass" />
          <OutcomeChip outcome="fail" />
          <OutcomeChip outcome="error" />
          <RunTypeLabel origin="fault" />
          <StepKey value="q1/retrieve#0" copy />
          <ScoreMeter score={0.74} />
          <StatChip>4 reused</StatChip>
          <FilterPill label="Outcome" value="Failed" />
        </div>
        <Tabs
          tabs={["Why", "I/O", "State", "Replay"]}
          active={tab}
          onChange={setTab}
        />
        <SegmentedControl
          options={["Seen", "Held-out", "Natural"]}
          value={segment}
          onChange={setSegment}
        />
        <Combobox
          value=""
          onChange={() => {}}
          options={[{ value: "demo", label: "Prepared demo question" }]}
        />
        <JsonViewer value={{ answer: "yes", confidence: 0.91 }} />
        <JsonEditor value={json} onChange={(value) => setJson(value)} />
        <PassageCard
          passage={{
            title: "Scott Derrickson",
            text: "Scott Derrickson is an American filmmaker.",
            score: 0.86,
          }}
        />
        <WordDiff parts={[" British", "-British", "+American"]} />
        <Skeleton />
        <KpiRow
          items={[
            { value: "84%", label: "finds the cause first" },
            { value: "71%", label: "on failure types it never saw" },
            { value: "63%", label: "on natural failures" },
            { value: "76%", label: "of steps reused" },
            { value: "1.2 ms", label: "per diagnosis" },
          ]}
        />
        <EmptyState title="No runs match these filters. Clear filters to see all runs." />
        <ErrorState />
      </section>
    </div>
  );
}

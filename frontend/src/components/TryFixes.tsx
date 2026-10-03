import { Check, LoaderCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useJob, useRepairJob } from "../api/hooks";
import { t } from "../lib/vocab";
import type { DiagnosisItem, RepairAttemptResponse } from "../api/types";
import { Button, Drawer, StatChip } from "./ui";

const names: Record<string, string> = {
  current_only: "Search current articles only",
  rewrite_query: "Rewrite the search query",
  widen_search: "Widen search to 6 results",
  entity_search: "Search by entity name",
  resample: "Ask again (new sample)",
  quote_first: "Quote evidence first, then answer",
  subanswers_only: "Use only the sub-answers",
  replan: "Re-plan with the question type",
};
export default function TryFixes({
  open,
  onClose,
  runId,
  ranking,
  onEdit,
  onFixFound,
}: {
  open: boolean;
  onClose: () => void;
  runId: string;
  ranking: DiagnosisItem[];
  onEdit: () => void;
  onFixFound?: (runId: string) => void;
}) {
  const repair = useRepairJob();
  const [jobId, setJobId] = useState<string>();
  const job = useJob(jobId);
  useEffect(() => {
    if (open && !jobId && !repair.isPending)
      repair.mutate(
        { id: runId },
        { onSuccess: (data) => setJobId(data.job_id) },
      );
  }, [open, jobId, repair, runId]);
  useEffect(() => {
    if (!open) setJobId(undefined);
  }, [open]);
  const result = job.data?.result as unknown as {
    repaired?: boolean;
    winning_run_id?: string;
    attempts?: RepairAttemptResponse[];
  } | null;
  const attempts = result?.attempts ?? [];
  const winningAttempt = attempts.find((attempt) => attempt.outcome === "pass");
  const done = job.data?.status === "completed";
  const failed = job.data?.status === "failed";
  const settled = done || failed;
  useEffect(() => {
    if (done && result?.repaired && result.winning_run_id)
      onFixFound?.(result.winning_run_id);
  }, [done, onFixFound, result?.repaired, result?.winning_run_id]);
  return (
    <Drawer open={open} title="Try fixes" onClose={onClose}>
      <p className="mb-6 text-sm text-graphite">
        Trying fixes on the top 3 likely causes, in order. Stops at the first
        fix that works.
      </p>
      <ol className="space-y-6">
        {ranking.slice(0, 3).map((rank, index) => (
          <li key={rank.step_key} className="grid grid-cols-[24px_1fr] gap-3">
            <span className="grid h-6 w-6 place-items-center rounded-full border border-rule font-mono text-xs">
              {index + 1}
            </span>
            <div>
              <div className="flex justify-between gap-3">
                <span className="font-mono text-xs">{rank.step_key}</span>
                <span
                  className={
                    index === 0
                      ? "text-xs text-orange"
                      : "text-xs text-graphite"
                  }
                >
                  {index === 0 ? "Most likely" : "Waiting"}
                </span>
              </div>
              <div className="mt-3 space-y-2">
                {attempts
                  .filter((attempt) => attempt.step_key === rank.step_key)
                  .map((attempt) => (
                    <div
                      key={attempt.run_id}
                      className="border-t border-rule-soft pt-2"
                    >
                      <div className="flex items-center gap-2 text-sm">
                        {attempt.outcome === "pass" ? (
                          <Check className="h-4 w-4 text-normal" />
                        ) : (
                          <X className="h-4 w-4 text-warning" />
                        )}
                        <span>
                          {names[attempt.strategy] ?? attempt.strategy}
                        </span>
                        <span
                          className={`ml-auto ${attempt.outcome === "pass" ? "text-normal" : "text-warning"}`}
                        >
                          {attempt.outcome === "pass" ? "Passed" : "Failed"}
                        </span>
                      </div>
                      <div className="mt-2 flex gap-2">
                        <StatChip>{attempt.n_executed} re-run</StatChip>
                        <StatChip>{attempt.n_reused} reused</StatChip>
                        {attempt.run_id && (
                          <Link
                            className="ml-auto text-xs text-advisory"
                            to={`/compare?a=${runId}&b=${attempt.run_id}`}
                          >
                            Compare
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                {!settled && index === 0 && (
                  <p className="flex items-center gap-2 text-sm text-graphite">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Trying fixes…
                  </p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
      {failed ? (
        <div className="mt-6 rounded-panel bg-caution-tint p-4">
          <p>
            The repair job failed before it could finish. Try again after the
            API is ready, or edit a step manually.
          </p>
          <Button className="mt-4" onClick={onEdit}>
            Edit a step manually
          </Button>
        </div>
      ) : done && result?.repaired ? (
        <div className="mt-6 rounded-panel bg-normal-tint p-4">
          <p className="font-medium">
            Fix found: {names[winningAttempt?.strategy ?? ""] ?? "working strategy"} on {ranking[0]?.step_key}.
          </p>
          <div className="mt-4 flex gap-2">
            <Link to={`/conversations/${result.winning_run_id}`} onClick={onClose}>
              <Button variant="ink">Open fixed {t("run")}</Button>
            </Link>
            <Link to={`/compare?a=${runId}&b=${result.winning_run_id}`}>
              <Button>Compare with original</Button>
            </Link>
          </div>
        </div>
      ) : done ? (
        <div className="mt-6 rounded-panel bg-caution-tint p-4">
          <p>
            No fix worked on the top 3 steps. Edit a step manually to keep
            investigating.
          </p>
          <Button className="mt-4" onClick={onEdit}>
            Edit a step manually
          </Button>
        </div>
      ) : null}
    </Drawer>
  );
}

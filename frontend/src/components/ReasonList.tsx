import type { DiagnosisReason } from "../api/types";

export default function ReasonList({
  reasons,
  limit = 3,
}: {
  reasons: DiagnosisReason[];
  limit?: number;
}) {
  if (!reasons.length)
    return (
      <p className="text-sm text-graphite">
        No explanation reasons were returned for this prediction.
      </p>
    );
  return (
    <div className="space-y-5">
      {reasons.slice(0, limit).map((reason) => (
        <div key={reason.feature}>
          <p className="text-md">{reason.text}</p>
          <blockquote className="mt-2 border-l-[3px] border-rule pl-3 text-xs text-graphite">
            {reason.evidence}
          </blockquote>
          <div className="mt-3 h-1 bg-rule-soft">
            <div
              className="h-full bg-caution"
              style={{ width: `${Math.min(100, reason.contribution * 180)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
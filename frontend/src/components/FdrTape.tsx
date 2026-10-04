import type { DiagnosisItem, StepRecord } from "../api/types";
import { CHART } from "../lib/chartColors";
export default function FdrTape({
  steps,
  ranking = [],
  selectedKey,
  hoverKey,
  onHover,
  onSelect,
  revealCount,
}: {
  steps: StepRecord[];
  ranking?: DiagnosisItem[];
  selectedKey?: string | null;
  hoverKey?: string | null;
  onHover?: (key: string | null) => void;
  onSelect?: (key: string) => void;
  revealCount?: number;
}) {
  const width = 1000;
  const height = 54;
  const column = width / Math.max(steps.length, 1);
  const score = (key: string, index: number) =>
    index < (revealCount ?? steps.length)
      ? (ranking.find((item) => item.step_key === key)?.score ?? 0)
      : 0;
  const points = steps.flatMap((step, index) => {
    const y = height - 8 - score(step.step_key, index) * 40;
    const start = index * column;
    return [
      [start, y],
      [start + column, y],
    ];
  });
  const path = points
    .map(([x, y], index) => `${index ? "L" : "M"}${x},${y}`)
    .join(" ");
  const activeIndex = steps.findIndex(
    (step) => step.step_key === (hoverKey ?? selectedKey),
  );
  if (!ranking.length)
    return (
      <div className="grid h-24 place-items-center border-t border-rule bg-panel text-sm text-graphite">
        Find the cause to see how suspicious each step is.
      </div>
    );
  return (
    <div
      className="relative h-24 border-t border-rule bg-panel px-3 pt-1"
      onMouseLeave={() => onHover?.(null)}
    >
      <svg
        viewBox={`0 0 ${width} 80`}
        preserveAspectRatio="none"
        className="h-full w-full"
        aria-label="FDR tape suspiciousness trace"
      >
        <path
          d={`${path} L${width},${height} L0,${height} Z`}
          fill="rgba(20,32,43,.08)"
        />
        <path
          d={path}
          fill="none"
          stroke={CHART.ink}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
        {steps.map((step, index) => {
          const rank = ranking.find(
            (item) => item.step_key === step.step_key,
          )?.rank;
          const x = index * column;
          return (
            <g
              key={step.step_key}
              onMouseEnter={() => onHover?.(step.step_key)}
              onClick={() => onSelect?.(step.step_key)}
              className="cursor-pointer"
            >
              <rect x={x} y="0" width={column} height="80" fill="transparent" />
              {rank === 1 && (
                <line
                  x1={x}
                  x2={x + column}
                  y1={height - 8 - score(step.step_key, index) * 40}
                  y2={height - 8 - score(step.step_key, index) * 40}
                  stroke={CHART.orange}
                  strokeWidth="3"
                />
              )}
              <line
                x1={x + column / 2}
                x2={x + column / 2}
                y1="56"
                y2="61"
                stroke={CHART.graphite}
              />
              <text
                x={x + column / 2}
                y="72"
                textAnchor="middle"
                fontFamily="B612 Mono"
                fontSize="8"
                fill={CHART.graphite}
              >
                {step.step_key.length > 15
                  ? `${step.step_key.slice(0, 13)}…`
                  : step.step_key}
              </text>
            </g>
          );
        })}
        {activeIndex >= 0 && (
          <g>
            <line
              x1={(activeIndex + 0.5) * column}
              x2={(activeIndex + 0.5) * column}
              y1="2"
              y2="61"
              stroke={CHART.ink}
            />
            <circle
              cx={(activeIndex + 0.5) * column}
              cy="4"
              r="3"
              fill={CHART.ink}
            />
          </g>
        )}
      </svg>
    </div>
  );
}

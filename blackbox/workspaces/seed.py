from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlmodel import func, select

from blackbox.store.db import get_session, init_db
from blackbox.store.models import Fault, Incident, Prediction, Run, Step, Task


@dataclass(frozen=True)
class Scenario:
    category: str
    question: str
    answer: str
    wrong_answer: str
    title: str
    cause_step: str
    cause_feature: str
    reason: str
    severity: str
    cost_inr: int


CLIENT_SCENARIOS: dict[str, tuple[Scenario, Scenario]] = {
    "aavya": (
        Scenario("returns", "Can I return an opened face serum?", "No, opened skincare products cannot be returned.", "Yes, within 30 days.", "Opened skincare products accepted for return", "retrieve", "archived_policy", "An archived returns policy ranked above the current hygiene policy.", "high", 18600),
        Scenario("ingredients", "Is the vitamin C serum fragrance-free?", "Yes, it is fragrance-free.", "No, it contains added fragrance.", "Fragrance-free products described incorrectly", "synthesize", "answer_support", "The answer contradicted the current ingredient sheet.", "medium", 9200),
    ),
    "bhoomi": (
        Scenario("delivery", "Do you deliver fresh produce to Pune on Sundays?", "Yes, Sunday delivery is available in Pune.", "No, deliveries run Monday to Saturday only.", "Sunday delivery availability answered incorrectly", "retrieve", "location_filter", "Search dropped the Pune service-area filter.", "medium", 12400),
        Scenario("refunds", "When will I receive a refund for a spoiled item?", "Within 3 business days.", "Within 10 business days.", "Spoilage refund timelines overstated", "extract", "numeric_mismatch", "The refund timeline was extracted from a general cancellation article.", "high", 21800),
    ),
    "jugnu": (
        Scenario("sizing", "What size should I buy for a 5-year-old?", "Choose size 5-6 years.", "Choose size 7-8 years.", "Children's size recommendations shifted upward", "extract", "table_alignment", "The age and size columns were misaligned during extraction.", "medium", 7600),
        Scenario("returns", "Can a personalised backpack be returned?", "No, personalised products are final sale.", "Yes, within 15 days.", "Personalised products incorrectly marked returnable", "retrieve", "missing_exception", "The personalisation exception was omitted from retrieved context.", "high", 16400),
    ),
    "taara": (
        Scenario("warranty", "Is tarnishing covered by the warranty?", "Manufacturing defects are covered, but normal tarnishing is not.", "Yes, all tarnishing is covered for one year.", "Tarnishing warranty coverage overstated", "synthesize", "policy_qualification", "The reply removed the normal-wear exclusion from the warranty.", "high", 27400),
        Scenario("shipping", "Is insured shipping included for orders over Rs 5,000?", "Yes, insured shipping is included.", "No, insurance always costs extra.", "Insured shipping benefit missed", "retrieve", "threshold_mismatch", "The order-value threshold was matched to an outdated shipping policy.", "medium", 11300),
    ),
    "vayu": (
        Scenario("charging", "Can I use a fast charger with the Vayu One?", "Use only the supplied standard charger.", "Yes, any 60V fast charger is supported.", "Unsafe fast-charger advice given", "synthesize", "safety_constraint", "The response ignored the battery safety constraint.", "critical", 48000),
        Scenario("service", "How often does my scooter need scheduled service?", "Every 4,000 km or 6 months.", "Every 10,000 km or 12 months.", "Service intervals stated incorrectly", "extract", "numeric_mismatch", "Distance and time values came from a discontinued model.", "high", 23600),
    ),
}


def seed_demo_clients() -> dict[str, int]:
    init_db()
    now = datetime.now(UTC).replace(microsecond=0)
    current_day = now.replace(hour=12, minute=0, second=0)
    with get_session() as session:
        for workspace, scenarios in CLIENT_SCENARIOS.items():
            for scenario_index, scenario in enumerate(scenarios):
                task_id = f"demo-{workspace}-task-{scenario_index + 1}"
                session.merge(
                    Task(
                        task_id=task_id,
                        workspace=workspace,
                        category=scenario.category,
                        question=scenario.question,
                        gold_answer=scenario.answer,
                        qtype="lookup",
                        level="medium",
                        split="test",
                        gold_titles=[f"{scenario.category.title()} policy"],
                        distractor_pids=[],
                    )
                )

            for run_index in range(18):
                scenario_index = run_index % len(scenarios)
                scenario = scenarios[scenario_index]
                failed = run_index % 3 == 0
                incident_index = (run_index // 3) % len(scenarios)
                incident_id = f"demo-{workspace}-incident-{incident_index + 1}"
                run_id = f"demo-{workspace}-run-{run_index + 1:02d}"
                step_key = "support/retrieve#0" if scenario.cause_step == "retrieve" else f"support/{scenario.cause_step}#0"
                created_at = current_day - timedelta(
                    days=run_index % 7, minutes=run_index
                )
                session.merge(
                    Run(
                        run_id=run_id,
                        task_id=f"demo-{workspace}-task-{scenario_index + 1}",
                        workspace=workspace,
                        incident_id=incident_id if failed else None,
                        origin="seeded",
                        final_answer=scenario.wrong_answer if failed else scenario.answer,
                        outcome="fail" if failed else "pass",
                        score_f1=0.0 if failed else 1.0,
                        n_steps=1,
                        n_reused=0,
                        n_executed=1,
                        tokens_total=180 + run_index * 3,
                        tokens_saved=0,
                        latency_ms=640 + run_index * 17,
                        created_at=created_at,
                    )
                )
                session.merge(
                    Step(
                        step_id=f"demo-{workspace}-step-{run_index + 1:02d}",
                        run_id=run_id,
                        step_key=step_key,
                        idx=0,
                        name=scenario.cause_step,
                        type="retrieval" if scenario.cause_step == "retrieve" else "llm",
                        node_id="support",
                        attempt=0,
                        deps=[],
                        input={"question": scenario.question},
                        input_hash=f"demo-input-{workspace}-{run_index}",
                        output={"answer": scenario.wrong_answer if failed else scenario.answer},
                        output_hash=f"demo-output-{workspace}-{run_index}",
                        output_text=scenario.wrong_answer if failed else scenario.answer,
                        latency_ms=640 + run_index * 17,
                        tokens_in=120,
                        tokens_out=60 + run_index * 3,
                        model="seeded-demo",
                        cache_hit=False,
                        reused=False,
                        overridden=False,
                        state_snapshot={},
                        meta={"seeded": True},
                    )
                )
                if failed:
                    session.merge(
                        Prediction(
                            run_id=run_id,
                            step_key=step_key,
                            score=0.91,
                            rank=1,
                            model_version="seeded-demo-v1",
                            reasons=[
                                {
                                    "feature": scenario.cause_feature,
                                    "text": scenario.reason,
                                    "evidence": scenario.wrong_answer,
                                    "contribution": 1.0,
                                }
                            ],
                        )
                    )
                    session.merge(
                        Fault(
                            run_id=run_id,
                            fault_type=scenario.cause_feature,
                            step_key=step_key,
                            params={"seeded": True},
                        )
                    )

            for scenario_index, scenario in enumerate(scenarios):
                incident_number = scenario_index + 1
                session.merge(
                    Incident(
                        incident_id=f"demo-{workspace}-incident-{incident_number}",
                        workspace=workspace,
                        group_key=f"{scenario.category}-{scenario.cause_feature}",
                        title=scenario.title,
                        category=scenario.category,
                        cause_step_name=scenario.cause_step,
                        cause_feature=scenario.cause_feature,
                        severity=scenario.severity,
                        status="investigating" if scenario_index == 0 else "open",
                        owner="Support AI team" if scenario_index == 0 else "",
                        est_cost_inr=scenario.cost_inr,
                        n_runs=3,
                        representative_run_id=f"demo-{workspace}-run-{scenario_index * 3 + 1:02d}",
                        first_seen=now - timedelta(days=6 - scenario_index),
                        last_seen=now - timedelta(hours=scenario_index * 4),
                    )
                )
        session.commit()
        return {
            "clients": len(CLIENT_SCENARIOS),
            "tasks": session.exec(
                select(func.count()).select_from(Task).where(Task.workspace.in_(CLIENT_SCENARIOS))
            ).one(),
            "runs": session.exec(
                select(func.count()).select_from(Run).where(Run.workspace.in_(CLIENT_SCENARIOS))
            ).one(),
            "incidents": session.exec(
                select(func.count()).select_from(Incident).where(Incident.workspace.in_(CLIENT_SCENARIOS))
            ).one(),
        }
from dataclasses import dataclass


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    display_name: str
    description: str


WORKSPACES = {
    "nimbu": Workspace(
        workspace_id="nimbu",
        display_name="Nimbu Living support",
        description="The business product and the demo story",
    ),
    "hotpot": Workspace(
        workspace_id="hotpot",
        display_name="Benchmark (HotpotQA)",
        description="Training data and the credible public-benchmark evaluation",
    ),
}
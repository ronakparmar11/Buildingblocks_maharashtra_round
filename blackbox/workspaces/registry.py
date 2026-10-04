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
        description="Customer support for an Indian home and kitchen store.",
    ),
    "aavya": Workspace(
        workspace_id="aavya",
        display_name="Aavya Skincare support",
        description="Customer support for a clean beauty and skincare brand.",
    ),
    "bhoomi": Workspace(
        workspace_id="bhoomi",
        display_name="Bhoomi Organics support",
        description="Customer support for an organic grocery marketplace.",
    ),
    "jugnu": Workspace(
        workspace_id="jugnu",
        display_name="Jugnu Kids support",
        description="Customer support for a children's clothing retailer.",
    ),
    "taara": Workspace(
        workspace_id="taara",
        display_name="Taara Jewellery support",
        description="Customer support for a contemporary jewellery brand.",
    ),
    "vayu": Workspace(
        workspace_id="vayu",
        display_name="Vayu Mobility support",
        description="Customer support for an electric scooter company.",
    ),
    "hotpot": Workspace(
        workspace_id="hotpot",
        display_name="Benchmark (HotpotQA)",
        description="Public benchmark and training workspace.",
    ),
}
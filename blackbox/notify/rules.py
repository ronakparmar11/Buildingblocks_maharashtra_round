from blackbox.store.models import Incident


def evaluate_rules(incident: Incident) -> None:
    del incident
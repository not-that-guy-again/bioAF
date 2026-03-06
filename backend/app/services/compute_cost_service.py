import logging

logger = logging.getLogger("bioaf.compute_cost")

# Static pricing lookup (approximate GCP prices USD/hour)
INSTANCE_PRICING = {
    "n2-highmem-8": {"on_demand": 0.5836, "spot": 0.1751},
    "n2-standard-4": {"on_demand": 0.1942, "spot": 0.0583},
    "n2-standard-8": {"on_demand": 0.3884, "spot": 0.1165},
    "n2-highmem-4": {"on_demand": 0.2918, "spot": 0.0875},
    "e2-standard-4": {"on_demand": 0.1340, "spot": 0.0402},
    "e2-standard-2": {"on_demand": 0.0670, "spot": 0.0201},
}


class ComputeCostService:
    @staticmethod
    def estimate_job_cost(instance_type: str, duration_hours: float, is_spot: bool = False) -> float:
        pricing = INSTANCE_PRICING.get(instance_type)
        if not pricing:
            return 0.0
        rate = pricing["spot"] if is_spot else pricing["on_demand"]
        return round(rate * duration_hours, 2)

    @staticmethod
    def get_cluster_burn_rate_from_nodes(active_nodes: int) -> float:
        """Estimate cost/hour based on active node count.

        Simplified: assumes a mix of standard and interactive nodes.
        """
        if active_nodes == 0:
            return 0.0
        # Rough estimate: average of standard spot + interactive on-demand
        avg_rate = (INSTANCE_PRICING["n2-highmem-8"]["spot"] + INSTANCE_PRICING["n2-standard-4"]["on_demand"]) / 2
        return round(active_nodes * avg_rate, 2)

    @staticmethod
    def get_monthly_spend_estimate(current_burn_rate: float) -> dict:
        """Estimate monthly spend from current burn rate."""
        hours_in_month = 730
        projected = round(current_burn_rate * hours_in_month, 2)

        alerts = []
        if projected > 5000:
            alerts.append("Projected spend exceeds $5,000/month")
        if projected > 10000:
            alerts.append("Projected spend exceeds $10,000/month")

        return {
            "monthly_budget": None,
            "current_spend": round(current_burn_rate * 24, 2),  # rough daily
            "projected_spend": projected,
            "threshold_alerts": alerts,
        }

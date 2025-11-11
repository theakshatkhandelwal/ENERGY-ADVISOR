from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable
from .calculations import (
	lighting_swap_savings_kwh,
	ac_setpoint_savings_kwh,
	standby_cut_savings_kwh,
	fridge_upgrade_savings_kwh,
	payback_months,
)


@dataclass
class Recommendation:
	code: str
	title: str
	details: Dict[str, Any]
	delta_kwh_month: float
	delta_cost_month: float
	delta_co2_month: float
	payback_months: float | None
	impact_score: float
	formula: str


def _impact_score(delta_cost_month: float, payback: float | None) -> float:
	# Simple composite: prioritize higher monthly savings and shorter payback
	payback_factor = 1.0 if payback is None else max(0.1, min(1.0, 12.0 / (payback + 1e-6)))
	return delta_cost_month * payback_factor


def generate_recommendations(
	appliances: Iterable[Any],
	tariff_r_per_kwh: float,
	ef_kg_per_kwh: float,
	assumptions: Dict[str, float] | None = None,
) -> List[Recommendation]:
	"""
	Basic rule-based recommendations using provided appliances.
	"""
	assumptions = assumptions or {}
	coeff_ac_per_deg = assumptions.get("ac_coefficient_per_degree", 0.04)
	default_led_w = assumptions.get("default_led_w", 9.0)
	default_standby_w = assumptions.get("default_standby_w", 10.0)
	default_standby_hours = assumptions.get("default_standby_hours", 2.0)

	recs: List[Recommendation] = []

	# Lighting swap: any bulb/fitting > default_led_w assumed convertible
	lighting_units = [a for a in appliances if a.type.lower() in {"bulb", "tube", "lighting"} and a.power_w > default_led_w]
	for a in lighting_units:
		delta_kwh = lighting_swap_savings_kwh(a.power_w, default_led_w, a.quantity, a.hours_per_day)
		delta_cost = delta_kwh * tariff_r_per_kwh
		delta_co2 = delta_kwh * ef_kg_per_kwh
		retrofit_cost = assumptions.get("lighting_cost_per_unit", 80.0) * a.quantity
		pb = payback_months(retrofit_cost, delta_cost)
		recs.append(
			Recommendation(
				code="lighting_swap",
				title=f"Swap {a.quantity}x {int(a.power_w)}W bulbs to {int(default_led_w)}W LEDs",
				details={"appliance_id": a.id, "p_old_w": a.power_w, "p_led_w": default_led_w, "n": a.quantity, "t": a.hours_per_day, "retrofit_cost": retrofit_cost},
				delta_kwh_month=round(delta_kwh, 2),
				delta_cost_month=round(delta_cost, 2),
				delta_co2_month=round(delta_co2, 2),
				payback_months=pb if pb is None else round(pb, 1),
				impact_score=_impact_score(delta_cost, pb),
				formula="ΔE = ((P_old − P_led) × N × T / 1000) × 30",
			)
		)

	# AC setpoint: find AC appliances; estimate monthly energy share from their daily
	ac_units = [a for a in appliances if a.type.lower() in {"ac", "air_conditioner", "air conditioner"}]
	for a in ac_units:
		e_ac_month = ((a.power_w * a.quantity * a.hours_per_day) / 1000.0) * 30.0
		delta_t = 2.0  # suggest +2 C
		delta_kwh = ac_setpoint_savings_kwh(e_ac_month, delta_t, coeff_ac_per_deg)
		delta_cost = delta_kwh * tariff_r_per_kwh
		delta_co2 = delta_kwh * ef_kg_per_kwh
		recs.append(
			Recommendation(
				code="ac_setpoint",
				title="Increase AC setpoint by +2 °C",
				details={"appliance_id": a.id, "e_ac_month": round(e_ac_month, 2), "delta_t": delta_t, "coefficient": coeff_ac_per_deg},
				delta_kwh_month=round(delta_kwh, 2),
				delta_cost_month=round(delta_cost, 2),
				delta_co2_month=round(delta_co2, 2),
				payback_months=0.0,
				impact_score=_impact_score(delta_cost, 0.1),
				formula="ΔE = E_AC × (0.04 × ΔT)",
			)
		)

	# Standby cut: generic suggestion across devices
	n_devices = max(len(list(appliances)), 1)
	delta_kwh = standby_cut_savings_kwh(default_standby_w, default_standby_hours, n_devices)
	if delta_kwh > 0:
		delta_cost = delta_kwh * tariff_r_per_kwh
		delta_co2 = delta_kwh * ef_kg_per_kwh
		recs.append(
			Recommendation(
				code="standby_cut",
				title="Eliminate standby power on idle devices",
				details={"p_s": default_standby_w, "t": default_standby_hours, "n": n_devices},
				delta_kwh_month=round(delta_kwh, 2),
				delta_cost_month=round(delta_cost, 2),
				delta_co2_month=round(delta_co2, 2),
				payback_months=0.0,
				impact_score=_impact_score(delta_cost, 0.1),
				formula="ΔE = (P_s × t × N / 1000) × 30",
			)
		)

	# Fridge upgrade: suggest if star_label looks old (e.g., '2-star')
	fridges = [a for a in appliances if a.type.lower() in {"fridge", "refrigerator"}]
	for a in fridges:
		# naive: estimate old/new annual kWh from star label
		old_year = 300.0 if (a.star_label or "").startswith("2") else 240.0
		new_year = 180.0
		delta_kwh = fridge_upgrade_savings_kwh(old_year, new_year)
		delta_cost = delta_kwh * tariff_r_per_kwh
		delta_co2 = delta_kwh * ef_kg_per_kwh
		retrofit_cost = 25000.0
		pb = payback_months(retrofit_cost, delta_cost)
		recs.append(
			Recommendation(
				code="fridge_upgrade",
				title="Upgrade to high-efficiency fridge",
				details={"e_old_year": old_year, "e_new_year": new_year, "retrofit_cost": retrofit_cost},
				delta_kwh_month=round(delta_kwh, 2),
				delta_cost_month=round(delta_cost, 2),
				delta_co2_month=round(delta_co2, 2),
				payback_months=pb if pb is None else round(pb, 1),
				impact_score=_impact_score(delta_cost, pb),
				formula="ΔE = (E_old − E_new) / 12",
			)
		)

	# Rank by ₹ saved/month
	recs.sort(key=lambda r: (-r.delta_cost_month, r.payback_months or 1e9))
	return recs



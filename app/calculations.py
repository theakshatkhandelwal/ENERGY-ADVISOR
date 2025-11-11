from __future__ import annotations
from typing import Iterable, Dict, Any

# Core Calculations per spec


def compute_daily_energy_kwh(appliances: Iterable[Any]) -> float:
	"""
	E_daily = Σ(P_i × N_i × T_i) / 1000
	Where T_i should reflect average daily hours; we expect appliance.daily_kwh() to provide this.
	"""
	return sum(getattr(a, "daily_kwh")() for a in appliances)


def compute_monthly_energy_kwh(e_daily_kwh: float) -> float:
	return e_daily_kwh * 30.0


def compute_monthly_cost(e_month_kwh: float, tariff_r_per_kwh: float) -> float:
	return e_month_kwh * tariff_r_per_kwh


def compute_monthly_co2(e_month_kwh: float, emission_factor_kg_per_kwh: float) -> float:
	return e_month_kwh * emission_factor_kg_per_kwh


# Measures (savings are monthly kWh unless noted)


def lighting_swap_savings_kwh(
	p_old_w: float,
	p_led_w: float,
	n_units: int,
	hours_per_day: float,
) -> float:
	"""
	ΔE = ((P_old − P_led) × N × T / 1000) × 30
	"""
	delta_watts = max(p_old_w - p_led_w, 0.0)
	return ((delta_watts * n_units * hours_per_day) / 1000.0) * 30.0


def ac_setpoint_savings_kwh(e_ac_month_kwh: float, delta_t_c: float, coefficient_per_degree: float = 0.04) -> float:
	"""
	ΔE = E_AC × (coefficient × ΔT)
	Default coefficient = 0.04 per degree C.
	"""
	return e_ac_month_kwh * (coefficient_per_degree * delta_t_c)


def standby_cut_savings_kwh(p_standby_w: float, hours_per_day: float, n_devices: int) -> float:
	"""
	ΔE = (P_s × t × N / 1000) × 30
	"""
	return ((p_standby_w * hours_per_day * n_devices) / 1000.0) * 30.0


def fridge_upgrade_savings_kwh(e_old_kwh_year: float, e_new_kwh_year: float) -> float:
	"""
	ΔE = (E_old − E_new) / 12
	"""
	return max(e_old_kwh_year - e_new_kwh_year, 0.0) / 12.0


def payback_months(retrofit_cost_r: float, delta_cost_r_per_month: float) -> float | None:
	"""
	Payback → retrofit_cost / ΔCost
	Returns None if delta_cost is zero or negative.
	"""
	if delta_cost_r_per_month <= 0:
		return None
	return retrofit_cost_r / delta_cost_r_per_month


def compute_kpis(appliances: Iterable[Any], tariff: float, ef: float) -> Dict[str, float]:
	"""
	Convenience KPI calculation bundle.
	"""
	e_daily = compute_daily_energy_kwh(appliances)
	e_month = compute_monthly_energy_kwh(e_daily)
	cost = compute_monthly_cost(e_month, tariff)
	co2 = compute_monthly_co2(e_month, ef)
	return {
		"daily_kwh": round(e_daily, 3),
		"monthly_kwh": round(e_month, 3),
		"monthly_cost": round(cost, 2),
		"monthly_co2": round(co2, 2),
	}



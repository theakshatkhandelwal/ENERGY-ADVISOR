import math
from app.calculations import (
	lighting_swap_savings_kwh,
	ac_setpoint_savings_kwh,
	standby_cut_savings_kwh,
	payback_months,
)


def test_lighting_swap():
	# 60W -> 9W, 5 bulbs, 6h/day → ((51*5*6)/1000)*30 = 45.9
	energy = lighting_swap_savings_kwh(60, 9, 5, 6)
	assert round(energy, 1) == 45.9


def test_ac_setpoint():
	# E_AC = 120 kWh/month, ΔT=2°C, coeff=0.04 → 9.6
	energy = ac_setpoint_savings_kwh(120, 2, 0.04)
	assert round(energy, 1) == 9.6


def test_standby_cut():
	# 10W, 2h/day, 12 devices → 7.2
	energy = standby_cut_savings_kwh(10, 2, 12)
	assert round(energy, 1) == 7.2


def test_payback():
	assert payback_months(1000, 0) is None
	assert payback_months(1000, -10) is None
	assert round(payback_months(1200, 100), 1) == 12.0



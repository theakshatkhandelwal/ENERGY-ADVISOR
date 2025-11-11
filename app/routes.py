from __future__ import annotations
import io
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from . import db
from .models import User, Appliance, Assumption, Scenario
from .calculations import compute_kpis, compute_daily_energy_kwh, compute_monthly_energy_kwh
from .recommendations import generate_recommendations
import pandas as pd

bp = Blueprint("main", __name__)


def _get_or_create_default_user() -> User:
	user = User.query.first()
	if not user:
		user = User(name="Demo User", tariff=8.0, ef=0.70, household_size=3, city="Delhi")
		db.session.add(user)
		db.session.commit()
	return user


def _assumptions_map() -> dict[str, float]:
	assumptions = {a.key: float(a.value) for a in Assumption.query.all()}
	# sensible defaults
	defaults = {
		"ac_coefficient_per_degree": 0.04,
		"default_led_w": 9.0,
		"default_standby_w": 10.0,
		"default_standby_hours": 2.0,
		"lighting_cost_per_unit": 80.0,
	}
	for k, v in defaults.items():
		assumptions.setdefault(k, v)
	return assumptions


@bp.route("/")
def index():
	return redirect(url_for("main.dashboard"))


@bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
	user = _get_or_create_default_user()
	if request.method == "POST":
		user.name = request.form.get("name", user.name)
		user.tariff = float(request.form.get("tariff", user.tariff or 8.0))
		user.ef = float(request.form.get("ef", user.ef or 0.70))
		user.household_size = int(request.form.get("household_size", user.household_size or 3))
		user.city = request.form.get("city", user.city)
		db.session.commit()
		flash("Profile updated", "success")
		return redirect(url_for("main.dashboard"))
	# KPI preview based on current appliances
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	kpis_preview = None
	if appliances_list:
		from .calculations import compute_kpis
		kpis_preview = compute_kpis(appliances_list, user.tariff, user.ef)
	return render_template("onboarding.html", user=user, kpis_preview=kpis_preview)


@bp.route("/appliances", methods=["GET", "POST"])
def appliances():
	user = _get_or_create_default_user()
	if request.method == "POST":
		a = Appliance(
			user_id=user.id,
			type=request.form.get("type", "device"),
			power_w=float(request.form.get("power_w", 0)),
			quantity=int(request.form.get("quantity", 1)),
			hours_per_day=float(request.form.get("hours_per_day", 1)),
			days_per_week=float(request.form.get("days_per_week", 7)),
			star_label=request.form.get("star_label", None),
		)
		db.session.add(a)
		db.session.commit()
		flash("Appliance added", "success")
		return redirect(url_for("main.appliances"))
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	return render_template("appliances.html", user=user, appliances=appliances_list)


@bp.route("/appliances/<int:appliance_id>/delete", methods=["POST"])
def delete_appliance(appliance_id: int):
	a = Appliance.query.get_or_404(appliance_id)
	db.session.delete(a)
	db.session.commit()
	flash("Appliance deleted", "info")
	return redirect(url_for("main.appliances"))


@bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
	user = _get_or_create_default_user()
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	kpis = compute_kpis(appliances_list, user.tariff, user.ef)
	assump = _assumptions_map()
	# Handle goals update
	if request.method == "POST":
		goal_kwh = request.form.get("goal_month_kwh")
		goal_cost = request.form.get("goal_month_cost")
		for key, raw in (("goal_month_kwh", goal_kwh), ("goal_month_cost", goal_cost)):
			if raw is None or raw == "":
				continue
			try:
				val = float(raw)
			except ValueError:
				continue
			existing = Assumption.query.filter_by(key=key).first()
			if existing:
				existing.value = val
			else:
				db.session.add(Assumption(key=key, value=val))
		db.session.commit()
		assump = _assumptions_map()
		flash("Goals updated", "success")

	# Pie chart: kWh/day share by appliance type
	type_to_kwh = {}
	for a in appliances_list:
		type_to_kwh[a.type] = type_to_kwh.get(a.type, 0.0) + a.daily_kwh()
	pie_labels = list(type_to_kwh.keys())
	pie_values = [round(v, 3) for v in type_to_kwh.values()]

	# Weekly trend (simple flat series from today's daily kWh)
	daily_kwh = kpis["daily_kwh"]
	line_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
	line_values = [daily_kwh] * 7

	# Top 5 hogs (by daily kWh)
	top_types = sorted(type_to_kwh.items(), key=lambda kv: kv[1], reverse=True)[:5]
	top_labels = [t for t, _ in top_types]
	top_values = [round(v, 3) for _, v in top_types]

	# Goals progress
	goal_month_kwh = float(assump.get("goal_month_kwh", 0) or 0)
	goal_month_cost = float(assump.get("goal_month_cost", 0) or 0)
	progress_kwh = 0
	progress_cost = 0
	if goal_month_kwh > 0:
		progress_kwh = int(max(0, min(100, (goal_month_kwh / max(kpis["monthly_kwh"], 0.0001)) * 100)))
	if goal_month_cost > 0:
		progress_cost = int(max(0, min(100, (goal_month_cost / max(kpis["monthly_cost"], 0.0001)) * 100)))

		return render_template(
		"dashboard.html",
		user=user,
		kpis=kpis,
		pie_labels=json.dumps(pie_labels),
		pie_values=json.dumps(pie_values),
		line_labels=json.dumps(line_labels),
		line_values=json.dumps(line_values),
		top_labels=json.dumps(top_labels),
		top_values=json.dumps(top_values),
		goal_month_kwh=goal_month_kwh,
		goal_month_cost=goal_month_cost,
		progress_kwh=progress_kwh,
		progress_cost=progress_cost,
	)

@bp.route("/recommendations", methods=["GET", "POST"])
def recommendations():
	user = _get_or_create_default_user()
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	assump = _assumptions_map()
	rank = request.args.get("rank", "cost")
	recs = generate_recommendations(appliances_list, user.tariff, user.ef, assump)
	if rank == "co2":
		recs.sort(key=lambda r: (-r.delta_co2_month, (r.payback_months or 1e9)))
	if request.method == "POST":
		name = request.form.get("name", "Apply All")
		saved_kwh = round(sum(r.delta_kwh_month for r in recs), 2)
		saved_cost = round(sum(r.delta_cost_month for r in recs), 2)
		saved_co2 = round(sum(r.delta_co2_month for r in recs), 2)
		sc = Scenario(
			user_id=user.id,
			name=name,
			measures_json=json.dumps([r.__dict__ for r in recs]),
			saved_kwh=saved_kwh,
			saved_cost=saved_cost,
			saved_co2=saved_co2,
		)
		db.session.add(sc)
		db.session.commit()
		flash(f"Scenario '{name}' created from all recommendations.", "success")
		return redirect(url_for("main.scenarios"))
	return render_template("recommendations.html", user=user, recs=recs, rank=rank)

@bp.route("/appliances/preset", methods=["POST"])
def appliances_preset():
	user = _get_or_create_default_user()
	pack = request.form.get("pack", "basic_2bhk")
	presets = []
	if pack == "basic_1bhk":
		presets = [
			{"type": "bulb", "power_w": 60, "quantity": 6, "hours_per_day": 5, "days_per_week": 7},
			{"type": "fan", "power_w": 70, "quantity": 2, "hours_per_day": 8, "days_per_week": 7},
			{"type": "fridge", "power_w": 110, "quantity": 1, "hours_per_day": 24, "days_per_week": 7, "star_label": "3-star"},
			{"type": "tv", "power_w": 80, "quantity": 1, "hours_per_day": 3, "days_per_week": 7},
		]
	else:
		presets = [
			{"type": "bulb", "power_w": 60, "quantity": 10, "hours_per_day": 6, "days_per_week": 7},
			{"type": "fan", "power_w": 70, "quantity": 4, "hours_per_day": 8, "days_per_week": 7},
			{"type": "AC", "power_w": 1200, "quantity": 1, "hours_per_day": 3, "days_per_week": 6},
			{"type": "fridge", "power_w": 120, "quantity": 1, "hours_per_day": 24, "days_per_week": 7, "star_label": "3-star"},
			{"type": "router", "power_w": 10, "quantity": 1, "hours_per_day": 24, "days_per_week": 7},
		]
	for p in presets:
		db.session.add(Appliance(user_id=user.id, **p))
	db.session.commit()
	flash("Preset appliances added", "success")
	return redirect(url_for("main.appliances"))

@bp.route("/appliances/remove_type", methods=["POST"])
def appliances_remove_type():
	user = _get_or_create_default_user()
	device_type = request.form.get("type")
	if not device_type:
		flash("No type provided", "warning")
		return redirect(url_for("main.appliances"))
	Appliance.query.filter_by(user_id=user.id, type=device_type).delete()
	db.session.commit()
	flash(f"Removed all '{device_type}' appliances.", "info")
	return redirect(url_for("main.appliances"))


@bp.route("/scenarios", methods=["GET", "POST"])
def scenarios():
	user = _get_or_create_default_user()
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	kpis_base = compute_kpis(appliances_list, user.tariff, user.ef)
	recs = generate_recommendations(appliances_list, user.tariff, user.ef, _assumptions_map())

	if request.method == "POST":
		selected_codes = request.form.getlist("measures")
		selected = [r for r in recs if r.code in selected_codes]
		saved_kwh = round(sum(r.delta_kwh_month for r in selected), 2)
		saved_cost = round(sum(r.delta_cost_month for r in selected), 2)
		saved_co2 = round(sum(r.delta_co2_month for r in selected), 2)
		sc = Scenario(
			user_id=user.id,
			name=request.form.get("name", "Scenario"),
			measures_json=json.dumps([r.__dict__ for r in selected]),
			saved_kwh=saved_kwh,
			saved_cost=saved_cost,
			saved_co2=saved_co2,
		)
		db.session.add(sc)
		db.session.commit()
		flash("Scenario saved", "success")
		return redirect(url_for("main.scenarios"))

	scenarios_list = Scenario.query.filter_by(user_id=user.id).all()
	# Prepare chart data for latest scenario if available
	bar_labels = []
	bar_values = []
	measure_labels = []
	measure_values = []
	if scenarios_list:
		latest = scenarios_list[-1]
		bar_labels = ["Baseline", latest.name]
		energy_after = max(kpis_base["monthly_kwh"] - latest.saved_kwh, 0.0)
		bar_values = [round(kpis_base["monthly_kwh"], 2), round(energy_after, 2)]
		# Savings by measure (kWh) for latest scenario
		try:
			measures = json.loads(latest.measures_json or "[]")
		except Exception:
			measures = []
		measure_labels = [m.get("title") or m.get("code", "") for m in measures]
		measure_values = [round(float(m.get("delta_kwh_month", 0.0)), 2) for m in measures]
	return render_template(
		"scenarios.html",
		user=user,
		kpis_base=kpis_base,
		recs=recs,
		scenarios=scenarios_list,
		bar_labels=json.dumps(bar_labels),
		bar_values=json.dumps(bar_values),
		measure_labels=json.dumps(measure_labels),
		measure_values=json.dumps(measure_values),
	)


@bp.route("/admin/assumptions", methods=["GET", "POST"])
def admin_assumptions():
	if request.method == "POST":
		for key, val in request.form.items():
			try:
				val_f = float(val)
			except ValueError:
				continue
			existing = Assumption.query.filter_by(key=key).first()
			if existing:
				existing.value = val_f
			else:
				db.session.add(Assumption(key=key, value=val_f))
		db.session.commit()
		flash("Assumptions updated", "success")
		return redirect(url_for("main.admin_assumptions"))
	return render_template("admin_assumptions.html", assumptions=_assumptions_map())


@bp.route("/export/csv")
def export_csv():
	user = _get_or_create_default_user()
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	rows = []
	for a in appliances_list:
		rows.append(
			{
				"type": a.type,
				"power_w": a.power_w,
				"quantity": a.quantity,
				"hours_per_day": a.hours_per_day,
				"days_per_week": a.days_per_week,
				"star_label": a.star_label or "",
				"daily_kwh": round(a.daily_kwh(), 3),
			}
		)
	kpis = compute_kpis(appliances_list, user.tariff, user.ef)
	df = pd.DataFrame(rows)
	buf = io.StringIO()
	df.to_csv(buf, index=False)
	buf.write("\n")
	buf.write("# KPIs\n")
	for k, v in kpis.items():
		buf.write(f"{k},{v}\n")
	mem = io.BytesIO(buf.getvalue().encode("utf-8"))
	return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="energy_report.csv")


@bp.route("/export/pdf")
def export_pdf():
	# Generate a simple PDF from dashboard-like HTML using WeasyPrint (if installed)
	try:
		from weasyprint import HTML  # type: ignore
	except Exception:
		flash("WeasyPrint not available on this environment. PDF export disabled.", "warning")
		return redirect(url_for("main.dashboard"))

	user = _get_or_create_default_user()
	appliances_list = Appliance.query.filter_by(user_id=user.id).all()
	kpis = compute_kpis(appliances_list, user.tariff, user.ef)
	html = render_template("export_pdf.html", user=user, kpis=kpis, appliances=appliances_list)
	pdf = HTML(string=html).write_pdf()
	return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name="energy_report.pdf")



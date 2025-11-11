from __future__ import annotations
from datetime import date
from typing import Optional
from . import db


class User(db.Model):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(120), nullable=False)
	tariff = db.Column(db.Float, nullable=False, default=8.0)  # ₹/kWh
	ef = db.Column(db.Float, nullable=False, default=0.70)  # kgCO2/kWh
	household_size = db.Column(db.Integer, nullable=False, default=3)
	city = db.Column(db.String(120), nullable=True)

	appliances = db.relationship("Appliance", backref="user", lazy=True, cascade="all, delete-orphan")
	logs = db.relationship("Log", backref="user", lazy=True, cascade="all, delete-orphan")
	measures = db.relationship("Measure", backref="user", lazy=True, cascade="all, delete-orphan")
	scenarios = db.relationship("Scenario", backref="user", lazy=True, cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<User {self.id} {self.name}>"


class Appliance(db.Model):
	__tablename__ = "appliances"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
	type = db.Column(db.String(80), nullable=False)  # bulb, fan, AC, fridge, etc.
	power_w = db.Column(db.Float, nullable=False)  # watts
	quantity = db.Column(db.Integer, nullable=False, default=1)
	hours_per_day = db.Column(db.Float, nullable=False, default=1.0)
	days_per_week = db.Column(db.Float, nullable=False, default=7.0)
	star_label = db.Column(db.String(20), nullable=True)  # e.g., "3-star", "5-star"

	def daily_kwh(self) -> float:
		# Convert to average daily usage factoring days_per_week
		avg_daily_hours = (self.hours_per_day * (self.days_per_week / 7.0))
		return (self.power_w * self.quantity * avg_daily_hours) / 1000.0

	def __repr__(self) -> str:
		return f"<Appliance {self.id} {self.type}>"


class Assumption(db.Model):
	__tablename__ = "assumptions"
	id = db.Column(db.Integer, primary_key=True)
	key = db.Column(db.String(120), unique=True, nullable=False)
	value = db.Column(db.Float, nullable=False)

	def __repr__(self) -> str:
		return f"<Assumption {self.key}={self.value}>"


class Log(db.Model):
	__tablename__ = "logs"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
	date = db.Column(db.Date, nullable=False, default=date.today)
	kwh = db.Column(db.Float, nullable=False)

	def __repr__(self) -> str:
		return f"<Log {self.user_id} {self.date} {self.kwh} kWh>"


class Measure(db.Model):
	__tablename__ = "measures"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
	code = db.Column(db.String(50), nullable=False)  # e.g., "lighting_swap"
	params_json = db.Column(db.Text, nullable=True)  # JSON string for parameters
	enabled = db.Column(db.Boolean, default=True, nullable=False)
	retrofit_cost = db.Column(db.Float, nullable=False, default=0.0)

	def __repr__(self) -> str:
		return f"<Measure {self.code} enabled={self.enabled}>"


class Scenario(db.Model):
	__tablename__ = "scenarios"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
	name = db.Column(db.String(120), nullable=False)
	measures_json = db.Column(db.Text, nullable=True)  # list of measure dicts
	saved_kwh = db.Column(db.Float, nullable=False, default=0.0)
	saved_cost = db.Column(db.Float, nullable=False, default=0.0)
	saved_co2 = db.Column(db.Float, nullable=False, default=0.0)

	def __repr__(self) -> str:
		return f"<Scenario {self.id} {self.name}>"



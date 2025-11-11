from app import create_app, db
from app.models import User, Appliance


def seed():
	app = create_app()
	with app.app_context():
		db.drop_all()
		db.create_all()

		user = User(name="Demo User", tariff=8.0, ef=0.70, household_size=3, city="Delhi")
		db.session.add(user)
		db.session.flush()

		appliances = [
			Appliance(user_id=user.id, type="bulb", power_w=60, quantity=5, hours_per_day=6, days_per_week=7),
			Appliance(user_id=user.id, type="fan", power_w=70, quantity=3, hours_per_day=8, days_per_week=7),
			Appliance(user_id=user.id, type="AC", power_w=1200, quantity=1, hours_per_day=3, days_per_week=6),
			Appliance(user_id=user.id, type="fridge", power_w=120, quantity=1, hours_per_day=24, days_per_week=7, star_label="3-star"),
			Appliance(user_id=user.id, type="tv", power_w=90, quantity=1, hours_per_day=3, days_per_week=7),
			Appliance(user_id=user.id, type="router", power_w=10, quantity=1, hours_per_day=24, days_per_week=7),
			Appliance(user_id=user.id, type="laptop", power_w=60, quantity=1, hours_per_day=4, days_per_week=6),
			Appliance(user_id=user.id, type="wm", power_w=500, quantity=1, hours_per_day=0.7, days_per_week=4),
			Appliance(user_id=user.id, type="geyser", power_w=2000, quantity=1, hours_per_day=0.5, days_per_week=5),
			Appliance(user_id=user.id, type="microwave", power_w=1200, quantity=1, hours_per_day=0.3, days_per_week=5),
		]
		db.session.add_all(appliances)
		db.session.commit()
		print("Seeded demo data.")


if __name__ == "__main__":
	seed()



from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pathlib import Path
import os
from sqlalchemy.pool import NullPool

db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config: dict | None = None) -> Flask:
	"""
	Application factory to create and configure the Flask app.
	"""
	app = Flask(__name__, instance_relative_config=True)

	# Default configuration
	app.config.from_mapping(
		SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
		SQLALCHEMY_DATABASE_URI=os.environ.get(
			"DATABASE_URL",
			f"sqlite:///{Path(app.instance_path) / 'app.sqlite'}",
		),
		SQLALCHEMY_TRACK_MODIFICATIONS=False,
	)

	# Ensure the instance folder exists
	try:
		os.makedirs(app.instance_path, exist_ok=True)
	except OSError:
		pass

	# Test configuration override
	if test_config:
		app.config.update(test_config)

	# Initialize extensions
	# Use NullPool in serverless to avoid holding connections
	engine_options = {"pool_pre_ping": True}
	if os.environ.get("VERCEL") or os.environ.get("SERVERLESS"):
		engine_options["poolclass"] = NullPool

	app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", engine_options)
	db.init_app(app)
	migrate.init_app(app, db)

	# Register blueprints
	from .routes import bp as main_bp

	app.register_blueprint(main_bp)

	# Create tables if not using migrations
	with app.app_context():
		from . import models  # noqa: F401
		db.create_all()

	return app



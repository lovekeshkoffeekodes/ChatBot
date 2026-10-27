# models.py
#
# NOTE: We are NOT using SQLAlchemy ORM models in this project.
# All database tables are defined and managed via raw SQL Alembic migrations.
#
# See: alembic/versions/ce744870efbf_create_custom_tables.py
#
# Tables:
#   - users          → stores registered users
#   - conversations  → stores chat threads (linked to users)
#   - messages       → stores individual messages (linked to conversations)

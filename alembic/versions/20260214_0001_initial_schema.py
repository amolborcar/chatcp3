"""Initial budget-mode schema."""

from alembic import op
import sqlalchemy as sa

revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dim_team",
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.Text(), nullable=False),
        sa.Column("abbreviation", sa.String(length=8), nullable=False),
        sa.Column("conference", sa.String(length=16), nullable=True),
        sa.Column("division", sa.String(length=32), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("team_id"),
    )

    op.create_table(
        "dim_player",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("primary_team_id", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["primary_team_id"], ["dim_team.team_id"]),
        sa.PrimaryKeyConstraint("player_id"),
    )

    op.create_table(
        "dim_game",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("season_type", sa.String(length=32), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("game_status", sa.String(length=32), nullable=True),
        sa.Column("game_status_text", sa.Text(), nullable=True),
        sa.Column("source_last_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["away_team_id"], ["dim_team.team_id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["dim_team.team_id"]),
        sa.PrimaryKeyConstraint("game_id"),
    )

    op.create_table(
        "fact_player_game_stats",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("opponent_team_id", sa.Integer(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("season_type", sa.String(length=32), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("started", sa.Boolean(), nullable=True),
        sa.Column("win", sa.Boolean(), nullable=True),
        sa.Column("minutes", sa.Numeric(5, 2), nullable=True),
        sa.Column("points", sa.Numeric(6, 2), nullable=True),
        sa.Column("rebounds", sa.Numeric(6, 2), nullable=True),
        sa.Column("assists", sa.Numeric(6, 2), nullable=True),
        sa.Column("steals", sa.Numeric(6, 2), nullable=True),
        sa.Column("blocks", sa.Numeric(6, 2), nullable=True),
        sa.Column("turnovers", sa.Numeric(6, 2), nullable=True),
        sa.Column("fg_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("fg3_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("ft_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("plus_minus", sa.Numeric(6, 2), nullable=True),
        sa.Column("source_endpoint", sa.Text(), nullable=False),
        sa.Column("data_version", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["game_id"], ["dim_game.game_id"]),
        sa.ForeignKeyConstraint(["opponent_team_id"], ["dim_team.team_id"]),
        sa.ForeignKeyConstraint(["player_id"], ["dim_player.player_id"]),
        sa.ForeignKeyConstraint(["team_id"], ["dim_team.team_id"]),
        sa.PrimaryKeyConstraint("game_id", "player_id"),
    )

    op.create_table(
        "fact_team_game_stats",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("opponent_team_id", sa.Integer(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("season_type", sa.String(length=32), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("win", sa.Boolean(), nullable=True),
        sa.Column("points", sa.Numeric(6, 2), nullable=True),
        sa.Column("rebounds", sa.Numeric(6, 2), nullable=True),
        sa.Column("assists", sa.Numeric(6, 2), nullable=True),
        sa.Column("steals", sa.Numeric(6, 2), nullable=True),
        sa.Column("blocks", sa.Numeric(6, 2), nullable=True),
        sa.Column("turnovers", sa.Numeric(6, 2), nullable=True),
        sa.Column("fg_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("fg3_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("ft_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("pace", sa.Numeric(6, 2), nullable=True),
        sa.Column("offensive_rating", sa.Numeric(6, 2), nullable=True),
        sa.Column("defensive_rating", sa.Numeric(6, 2), nullable=True),
        sa.Column("net_rating", sa.Numeric(6, 2), nullable=True),
        sa.Column("source_endpoint", sa.Text(), nullable=False),
        sa.Column("data_version", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["game_id"], ["dim_game.game_id"]),
        sa.ForeignKeyConstraint(["opponent_team_id"], ["dim_team.team_id"]),
        sa.ForeignKeyConstraint(["team_id"], ["dim_team.team_id"]),
        sa.PrimaryKeyConstraint("game_id", "team_id"),
    )

    op.create_table(
        "data_quality_run",
        sa.Column("run_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("checks_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checks_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("run_id"),
    )

    op.create_index("idx_fpgs_player_date", "fact_player_game_stats", ["player_id", "game_date"])
    op.create_index("idx_fpgs_team_date", "fact_player_game_stats", ["team_id", "game_date"])
    op.create_index("idx_fpgs_opponent_date", "fact_player_game_stats", ["opponent_team_id", "game_date"])
    op.create_index("idx_fpgs_season_type", "fact_player_game_stats", ["season", "season_type"])
    op.create_index("idx_ftgs_team_date", "fact_team_game_stats", ["team_id", "game_date"])
    op.create_index("idx_ftgs_season_type", "fact_team_game_stats", ["season", "season_type"])
    op.create_index("idx_dim_game_date", "dim_game", ["game_date"])
    op.create_index("idx_dim_game_season_type", "dim_game", ["season", "season_type"])


def downgrade() -> None:
    op.drop_index("idx_dim_game_season_type", table_name="dim_game")
    op.drop_index("idx_dim_game_date", table_name="dim_game")
    op.drop_index("idx_ftgs_season_type", table_name="fact_team_game_stats")
    op.drop_index("idx_ftgs_team_date", table_name="fact_team_game_stats")
    op.drop_index("idx_fpgs_season_type", table_name="fact_player_game_stats")
    op.drop_index("idx_fpgs_opponent_date", table_name="fact_player_game_stats")
    op.drop_index("idx_fpgs_team_date", table_name="fact_player_game_stats")
    op.drop_index("idx_fpgs_player_date", table_name="fact_player_game_stats")
    op.drop_table("data_quality_run")
    op.drop_table("fact_team_game_stats")
    op.drop_table("fact_player_game_stats")
    op.drop_table("dim_game")
    op.drop_table("dim_player")
    op.drop_table("dim_team")


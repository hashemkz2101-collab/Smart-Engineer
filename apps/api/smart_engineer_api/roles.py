"""Role identities and project vocabulary for Phase 1.

The master specification (section 2) names six roles. Five are project-scoped
professional roles stored on ``project_members``; the sixth, the system
administrator, is a platform-level flag on ``users`` and never a project role.
Organization membership roles are separate and only describe who manages an
organization (the tenant), not what someone may do on an engineering project.
"""

PROJECT_ROLES = (
    "owner",  # owner / client (spec 2.1)
    "architect",  # architect (spec 2.2)
    "structural_engineer",  # structural engineer (spec 2.3)
    "mep_engineer",  # mechanical and electrical engineer (spec 2.4)
    "quantity_surveyor",  # quantity surveyor / estimator (spec 2.5)
)
SYSTEM_ADMIN = "system_admin"  # platform administrator (spec 2.6), flag on users
ROLE_IDENTITIES = (*PROJECT_ROLES, SYSTEM_ADMIN)

ORG_ROLES = ("owner", "admin", "member")
# Ownership cannot be granted by invitation (no ownership transfer in Phase 1).
INVITABLE_ORG_ROLES = ("admin", "member")

# Initial market project types are a Phase 1 default (DEC-003, owner-delegated
# assistant proposal). More types can be added by a migration.
PROJECT_TYPES = (
    "residential_house",
    "residential_apartment",
    "commercial",
    "mixed_use",
    "other",
)

PROJECT_STATUSES = ("active", "archived")

INTAKE_STEPS = ("identity", "location", "people", "legal")

# Site / land data sections (SITE-001, SITE-002).
SITE_SECTIONS = ("parcel", "access", "terrain", "surroundings", "soil")

# Environmental / technical condition inputs (ENV-001, master spec 3.5).
ENV_FIELDS = (
    "climate",
    "solar",
    "wind",
    "rainfall",
    "design_temperature",
    "hazards",
    "seismicity",
    "water",
    "electricity",
    "gas",
    "sewer",
    "telecom",
    "energy",
)

# Client requirement sections (REQ-001, REQ-002, REQ-003).
REQUIREMENT_SECTIONS = ("program", "preferences", "references")

# Zoning / building-control input categories (RULE-DATA-001, master spec 3.3).
ZONING_FIELDS = (
    "land_use",
    "coverage",
    "density",
    "floors_height",
    "setbacks",
    "parking_access",
    "daylight_openings",
    "circulation",
    "local_constraints",
)

AUTH_TOKEN_PURPOSES = ("password_reset", "email_verification")


def sql_in(column: str, values: tuple[str, ...]) -> str:
    """Build a CHECK expression ``column IN ('a', 'b', ...)`` from fixed values."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"

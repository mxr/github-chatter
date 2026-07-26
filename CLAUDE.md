# Preferences

- Prefer typed dataclasses over `dict[str, Any]` for internal data models (e.g. coordinator output). Use `@dataclass(frozen=True, slots=True)`. External API payloads (raw GitHub API JSON) can stay as `dict[str, Any]` since that's an external boundary.

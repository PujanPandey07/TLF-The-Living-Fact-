class NotFoundError(Exception):
    """Raised when a place name doesn't match anything in places.yaml."""

    def __init__(self, query, district=None, level=None):
        self.query = query
        self.district = district
        self.level = level
        message = f"No place found matching '{query}'"
        if district:
            message += f" in district '{district}'"
        if level:
            message += f" at level '{level}'"

        # Exception.__init__ sets self.args and makes str(e) work correctly
        super().__init__(message)


class AmbiguityError(Exception):
    """Raised when a place name matches more than one place and can't be
    resolved without more information (district, district_code, or level)."""

    def __init__(self, query, candidates):
        self.query = query
        self.candidates = candidates

        # build a readable label per candidate — fall back to the level
        # itself when there's no district (district/province-level
        # candidates legitimately have district=None, since a district
        # has no parent district to report)
        labels = [
            c["district"] if c.get("district") else f"the {c['level']} level"
            for c in candidates
        ]
        district_list = ", ".join(labels)

        message = (
            f"'{query}' is ambiguous — matches {len(candidates)} places "
            f"in: {district_list}. Pass district= or district_code= to disambiguate."
        )

        super().__init__(message)


class FuzzyMatchError(Exception):
    """Raised when a place name has no exact match (even after suffix
    stripping), but similar names were found via fuzzy matching.
    Carries the top candidates so the caller can show a 'did you mean?' prompt."""

    def __init__(self, query, candidates):
        # the original (unmatched) query string
        self.query = query

        # list of (name_or_dict, score) tuples — top 3 closest matches
        # score is a similarity measure (e.g. 0-100 from rapidfuzz)
        # kept as tuples so score isn't buried inside a dict callers must dig into
        self.candidates = candidates

        # human-readable message showing the top guesses and their scores
        suggestions = ", ".join(
            f"{name} ({score:.0f}%)" for name, score in candidates
        )
        message = (
            f"No exact match for '{query}'. Did you mean: {suggestions}?"
        )

        super().__init__(message)

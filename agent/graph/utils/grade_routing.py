"""Pure routing decisions after generation grading."""


def resolve_generation_grade_route(
    *,
    has_documents: bool,
    answer_useful: bool,
    grounded: bool | None,
    retry_count: int,
) -> str:
    """Map grader outcomes to after_generate edge labels.

    Returns:
        One of: useful, not useful, need search web, end_misery
    """
    if answer_useful:
        return "useful"
    if not has_documents or not grounded:
        if retry_count < 1:
            return "need search web"
        return "end_misery"
    return "not useful"

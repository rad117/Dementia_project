"""Task registry -- maps a task_id (as sent by the frontend, stored on the
assessment row) to display name and expected-concept count.

expected_concepts count is sourced from ml.nlp.linguistic's
_COOKIE_THEFT_CONCEPTS (the concept list the trained model's
cookie_theft_concept_count/ratio features and ml.nlp.semantic's
concepts_identified/expected actually score against), not duplicated here
-- so the denominator shown to a clinician always matches what the ML
layer computed the numerator against.

Note: frontend/src/data/mockTasks.js's pictureDescriptionTask describes a
different custom illustration with its own 16-item expectedConcepts list
(kitchen, tilting, reaching, cat, tree, falling, ...) that does not match
ml.nlp.linguistic's 15-item classic Cookie Theft concept set. That's a
content-alignment question for the research team (the concept list is
part of the scoring methodology, not backend plumbing) -- this registry
intentionally reuses the ML-side list, since that's what the trained
model and concept-coverage score are actually built on.
"""

from ml.nlp.linguistic import _COOKIE_THEFT_CONCEPTS

TASKS: dict[str, dict] = {
    "cookie-theft": {
        "name": "Picture Description",
        "expected_concepts": len(_COOKIE_THEFT_CONCEPTS),
    },
}

_DEFAULT_TASK = {"name": "Picture Description", "expected_concepts": len(_COOKIE_THEFT_CONCEPTS)}


def get_task(task_id: str) -> dict:
    """Never raises -- an unknown task_id (e.g. legacy data) falls back to
    the default task's display name/concept count rather than erroring
    a results page over cosmetic metadata."""
    return TASKS.get(task_id, _DEFAULT_TASK)

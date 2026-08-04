"""The WP-017 corpus-grounded retrieval-evaluation fixture (section 12).

Every ``expected_literal_term`` below was verified, by direct inspection of
the real ``data/student_summary_*.pdf`` corpus (character-level substring
search over ``build_student_summary_corpus()``'s actual chunk text, not
TF-IDF ranking output - a term appearing in the top-ranked chunk is not
evidence that the term is genuinely present unless independently checked),
to actually occur at least once. Nothing here is fabricated from general
neuroanatomy knowledge (WP-017 section 12's explicit requirement).

``RetrievalEvaluationRunner`` re-checks literal containment fresh against
whatever corpus it is given at evaluation time - this module supplies only
the query/expected-term pairs, never a hardcoded chunk-id list, so the
fixture cannot silently go stale if the corpus or chunking configuration
changes.

Covers all 20 real canonical categories at least once: 17 via their exact
category-name text (which literally appears in the corpus for those 17),
and the remaining 3 (``מיפוי ודימות מוחי``, ``קרומים וסינוסים דוראליים``,
``מסילות עצביות``) via a verified alternate term, since their exact
category-name phrase does not itself appear verbatim anywhere in the
corpus - itself a real, useful finding (see docs/PROJECT_STATUS.md).
"""

from __future__ import annotations

from exam_generator.evaluation.models import RetrievalEvalQuery

RETRIEVAL_EVAL_QUERIES: tuple[RetrievalEvalQuery, ...] = (
    # --- Canonical category names (17 of 20; literal match confirmed) ---
    RetrievalEvalQuery(query="התעלה השדרתית ותכולתה", expected_literal_term="התעלה השדרתית ותכולתה", category="התעלה השדרתית ותכולתה"),
    RetrievalEvalQuery(query="לוקליזציה פונקציונלית", expected_literal_term="לוקליזציה פונקציונלית", category="לוקליזציה פונקציונלית"),
    RetrievalEvalQuery(query="חומר לבן", expected_literal_term="חומר לבן", category="חומר לבן"),
    RetrievalEvalQuery(query="עצבים קרניאליים", expected_literal_term="עצבים קרניאליים", category="עצבים קרניאליים"),
    RetrievalEvalQuery(query="היסטולוגיה", expected_literal_term="היסטולוגיה", category="היסטולוגיה"),
    RetrievalEvalQuery(query="המערכת הלימבית", expected_literal_term="המערכת הלימבית", category="המערכת הלימבית"),
    RetrievalEvalQuery(query="אספקת דם", expected_literal_term="אספקת דם", category="אספקת דם"),
    RetrievalEvalQuery(query="גזע המוח", expected_literal_term="גזע המוח", category="גזע המוח"),
    RetrievalEvalQuery(query="גרעיני הבסיס", expected_literal_term="גרעיני הבסיס", category="גרעיני הבסיס"),
    RetrievalEvalQuery(query="המוח הקטן", expected_literal_term="המוח הקטן", category="המוח הקטן"),
    RetrievalEvalQuery(query="מערכת העצבים ההיקפית", expected_literal_term="מערכת העצבים ההיקפית", category="מערכת העצבים ההיקפית"),
    RetrievalEvalQuery(query="דיאנצפלון", expected_literal_term="דיאנצפלון", category="דיאנצפלון"),
    RetrievalEvalQuery(query="אמבריולוגיה", expected_literal_term="אמבריולוגיה", category="אמבריולוגיה"),
    RetrievalEvalQuery(query="טופוגרפיה של ההמיספרות", expected_literal_term="טופוגרפיה של ההמיספרות", category="טופוגרפיה של ההמיספרות"),
    RetrievalEvalQuery(query="חדרי המוח", expected_literal_term="חדרי המוח", category="חדרי המוח"),
    RetrievalEvalQuery(query="תאי מערכת העצבים", expected_literal_term="תאי מערכת העצבים", category="תאי מערכת העצבים"),
    RetrievalEvalQuery(query="מבוא", expected_literal_term="מבוא", category="מבוא"),
    # --- Remaining 3 categories: exact category-name phrase not found
    # verbatim in the corpus (a real WP-006-consistent finding - summary
    # wording differs from canonical exam-category wording); verified
    # alternate term used instead ---
    RetrievalEvalQuery(
        query="מיפוי ודימות מוחי",
        expected_literal_term="דימות",
        category="מיפוי ודימות מוחי",
        note="exact category phrase not found verbatim in corpus; 'דימות' (imaging) is",
    ),
    RetrievalEvalQuery(
        query="קרומים וסינוסים דוראליים",
        expected_literal_term="dural",
        category="קרומים וסינוסים דוראליים",
        note="exact category phrase not found verbatim in corpus; English 'dural' is",
    ),
    RetrievalEvalQuery(
        query="מסילות עצביות",
        expected_literal_term="tract",
        category="מסילות עצביות",
        note="exact category phrase not found verbatim in corpus; English 'tract' is",
    ),
    # --- Specific anatomical terms: Hebrew/English/mixed, granular
    # (below the level of a whole category name) ---
    RetrievalEvalQuery(query="Vertebral Foramen", expected_literal_term="Vertebral Foramen", category="התעלה השדרתית ותכולתה"),
    RetrievalEvalQuery(query="Medulla Oblongata", expected_literal_term="Medulla Oblongata", category="גזע המוח"),
    RetrievalEvalQuery(query="Corticospinal tract", expected_literal_term="Corticospinal", category="מסילות עצביות"),
    RetrievalEvalQuery(query="גסטרולציה שלב עוברי", expected_literal_term="Gastrulation", category="אמבריולוגיה"),
    RetrievalEvalQuery(query="Central Sulcus", expected_literal_term="Central Sulcus", category="טופוגרפיה של ההמיספרות"),
    RetrievalEvalQuery(query="Hippocampus", expected_literal_term="Hippocampus", category="המערכת הלימבית"),
    RetrievalEvalQuery(query="thalamus", expected_literal_term="thalamus", category="דיאנצפלון"),
    RetrievalEvalQuery(query="Cerebellum", expected_literal_term="Cerebellum", category="המוח הקטן"),
    RetrievalEvalQuery(query="ventricle", expected_literal_term="ventricle", category="חדרי המוח"),
    RetrievalEvalQuery(query="blood supply", expected_literal_term="blood supply", category="אספקת דם"),
    RetrievalEvalQuery(query="Cranial Nerve", expected_literal_term="Cranial Nerve", category="עצבים קרניאליים"),
    RetrievalEvalQuery(query="white matter tracts", expected_literal_term="white matter", category="חומר לבן"),
    RetrievalEvalQuery(query="Basal Ganglia", expected_literal_term="Basal Ganglia", category="גרעיני הבסיס"),
    RetrievalEvalQuery(query="neural tube development", expected_literal_term="neural tube", category="אמבריולוגיה"),
    RetrievalEvalQuery(query="sulcus and gyrus", expected_literal_term="sulcus", category="טופוגרפיה של ההמיספרות"),
    RetrievalEvalQuery(query="foramen magnum", expected_literal_term="foramen magnum", category="גזע המוח"),
    RetrievalEvalQuery(query="brainstem structure", expected_literal_term="brainstem", category="גזע המוח"),
)

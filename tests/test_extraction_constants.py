from shared.constants import DOC_TYPE_FIELD_CATALOG, REQUIRED_DOC_TYPES, REQUIRED_STATEMENT_FIELDS
from shared.queue import ANALYZE_QUEUE, EXTRACTION_QUEUE, SLINK_SCORING_QUEUE


def test_doc_type_field_catalog_covers_every_required_doc_type():
    assert set(DOC_TYPE_FIELD_CATALOG) == REQUIRED_DOC_TYPES


def test_financial_statement_catalog_reuses_existing_constant():
    assert DOC_TYPE_FIELD_CATALOG["financial_statement"] is REQUIRED_STATEMENT_FIELDS


def test_every_catalog_entry_is_a_non_empty_frozenset():
    for doc_type, fields in DOC_TYPE_FIELD_CATALOG.items():
        assert isinstance(fields, frozenset), doc_type
        assert fields, doc_type


def test_extraction_queue_name_is_unique_from_other_queues():
    assert len({ANALYZE_QUEUE, EXTRACTION_QUEUE, SLINK_SCORING_QUEUE}) == 3

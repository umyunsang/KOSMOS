"""Retrieval backend subpackage (spec 026).

Pluggable ranking strategies consumed by ``ToolRegistry``:
BM25 (default), Dense (opt-in), Hybrid (opt-in).

The external contract owned by spec 507 (``LookupSearchInput``,
``LookupSearchResult``, ``AdapterCandidate``, ``GovAPITool``) remains
byte-identical; see ``contracts/retriever_protocol.md`` for the
internal ``Retriever`` protocol.
"""

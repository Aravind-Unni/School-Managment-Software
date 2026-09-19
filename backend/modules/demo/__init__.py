"""M00 demo: the placeholder module that proves the foundation works.

Owns no business domain. A "note" here is deliberately meaningless scaffolding:
it exercises the shared machinery end to end -- UUID + school_id + version,
optimistic concurrency, the error envelope, cursor pagination, an Access check
through the host scope resolver, and an audit row plus an outbox event written in
the caller's transaction.

When the fourteen real modules arrive, this module stays: it is the regression
test for the foundation itself.
"""

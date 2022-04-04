class SoftDeleteDBRouter:
    """Route queries to different schemas."""

    def db_for_read(self, model, **hints):
        """Return db for read operations."""
        if model._meta.db_table.startswith("deleted_"):  # noqa: WPS437 protected
            return "deleted"
        return "default"

    def db_for_write(self, model, **hints):
        """Return db for write operations."""
        if model._meta.db_table.startswith("deleted_"):  # noqa: WPS437 protected
            return "deleted"
        return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Allow migration or not."""
        # first check runSql and runPython commands
        if hints.get("using_db") is not None:
            return db == hints["using_db"]

        if model_name is None:
            return None

        if db == "default":
            return app_label != "soft_deleted"
        elif db == "deleted":
            return app_label == "soft_deleted"

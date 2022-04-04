import typing as tp

# this is an example
_create_schema_sql = """
create schema if not exists deleted;
GRANT ALL ON SCHEMA deleted TO "{db_user}";
"""

soft_delete_functions_sql = """
create or replace function soft_delete()
    returns trigger as
$$
declare
    deleted_table text := format('%I.deleted_%I', 'deleted', tg_table_name);
    copy_query    text := format('insert into %s values (($1).*) ', deleted_table);
begin
    if tg_table_schema != 'public' then
        raise exception
            'The trigger can be applied to the public schema only, got % instead',
            tg_table_schema;
    end if;

    old.deleted_at = now();
    execute copy_query using old;

    return old;
end
$$ language plpgsql;


create or replace function soft_restore()
    returns trigger as
$$
declare
    original_table text := format('%I.%I', 'public', replace(tg_table_name, 'deleted_', ''));
    deleted_table  text := format('%I.%I', tg_table_schema, tg_table_name);
    copy_query     text := format('insert into %s values (($1).*)', original_table);
    delete_query   text := format('delete from %s where id = $1', deleted_table);
begin
    if tg_table_schema != 'deleted' then
        raise exception
            'The trigger can be applied to the deleted schema only, got % instead',
            tg_table_schema;
    end if;

    if new.deleted_at is null then
        execute copy_query using new;
        execute delete_query using new.id;
    end if;

    return old;
end
$$ language plpgsql;


create or replace function prevent_deletion()
    returns trigger as
$$
declare
begin
    if tg_table_schema != 'deleted' then
        raise exception
            'The trigger can be applied to the deleted schema only, got % instead',
            tg_table_schema;
    end if;

    if old.deleted_at is not null then
        raise exception
            'Deletion from tables in `deleted` schema is forbidden. You can only restore records to the public schema. To do this set deleted_at = null.';
    end if;

    return old;
end
$$ language plpgsql;
"""  # noqa: E501, WPS323 too long and % format


def get_soft_delete_sql_triggers(table: str) -> tp.Tuple[tp.List[str], tp.List[str]]:
    """Return table triggers for default and deleted schemas."""
    default_triggers = []
    deleted_triggers = []

    default_triggers.append(f"drop trigger if exists {table}_soft_delete on public.{table};")
    default_triggers.append(
        f"create trigger {table}_soft_delete before delete on public.{table} for each row execute procedure soft_delete();",  # noqa: E501 too long
    )
    deleted_triggers.append(
        f"drop trigger if exists {table}_soft_restore on deleted.deleted_{table};",
    )
    deleted_triggers.append(
        f"create trigger {table}_soft_restore after update on deleted.deleted_{table} for each row execute procedure soft_restore();",  # noqa: E501 too long
    )
    deleted_triggers.append(
        f"drop trigger if exists {table}_prevent_deletion on deleted.deleted_{table};",
    )
    deleted_triggers.append(
        f"create trigger {table}_prevent_deletion before delete on deleted.deleted_{table} for each row execute procedure prevent_deletion();",  # noqa: E501 too long
    )
    return default_triggers, deleted_triggers

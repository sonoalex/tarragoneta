import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Exclude PostGIS/TIGER tables from migrations
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table":
            postgis_tables = {
                'spatial_ref_sys', 'geometry_columns', 'geography_columns',
                'raster_columns', 'raster_overviews',
                'addr', 'addrfeat', 'bg', 'county', 'county_lookup',
                'countysub_lookup', 'cousub', 'direction_lookup', 'edges',
                'faces', 'featnames', 'geocode_settings', 'geocode_settings_default',
                'layer', 'loader_lookuptables', 'loader_platform', 'loader_variables',
                'pagc_gaz', 'pagc_lex', 'pagc_rules', 'place', 'place_lookup',
                'secondary_unit_lookup', 'state', 'state_lookup', 'street_type_lookup',
                'tabblock', 'tabblock20', 'topology', 'tract', 'zcta5',
                'zip_lookup', 'zip_lookup_all', 'zip_lookup_base', 'zip_state',
                'zip_state_loc'
            }
            if name in postgis_tables:
                return False
        return True

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True,
        include_object=include_object
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    # Exclude PostGIS/TIGER tables and system tables from migrations
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table":
            # Exclude PostGIS system schemas
            if hasattr(object, 'schema') and object.schema:
                if object.schema in ('tiger', 'topology', 'public'):
                    # In public schema, exclude PostGIS/TIGER tables
                    postgis_tables = {
                        'spatial_ref_sys', 'geometry_columns', 'geography_columns',
                        'raster_columns', 'raster_overviews',
                        # TIGER tables
                        'addr', 'addrfeat', 'bg', 'county', 'county_lookup',
                        'countysub_lookup', 'cousub', 'direction_lookup', 'edges',
                        'faces', 'featnames', 'geocode_settings', 'geocode_settings_default',
                        'layer', 'loader_lookuptables', 'loader_platform', 'loader_variables',
                        'pagc_gaz', 'pagc_lex', 'pagc_rules', 'place', 'place_lookup',
                        'secondary_unit_lookup', 'state', 'state_lookup', 'street_type_lookup',
                        'tabblock', 'tabblock20', 'topology', 'tract', 'zcta5',
                        'zip_lookup', 'zip_lookup_all', 'zip_lookup_base', 'zip_state',
                        'zip_state_loc'
                    }
                    if name in postgis_tables:
                        return False
                elif object.schema not in (None, 'public'):
                    # Exclude all non-public schemas
                    return False
            else:
                # Tables without schema - exclude PostGIS/TIGER tables
                postgis_tables = {
                    'spatial_ref_sys', 'geometry_columns', 'geography_columns',
                    'raster_columns', 'raster_overviews',
                    'addr', 'addrfeat', 'bg', 'county', 'county_lookup',
                    'countysub_lookup', 'cousub', 'direction_lookup', 'edges',
                    'faces', 'featnames', 'geocode_settings', 'geocode_settings_default',
                    'layer', 'loader_lookuptables', 'loader_platform', 'loader_variables',
                    'pagc_gaz', 'pagc_lex', 'pagc_rules', 'place', 'place_lookup',
                    'secondary_unit_lookup', 'state', 'state_lookup', 'street_type_lookup',
                    'tabblock', 'tabblock20', 'topology', 'tract', 'zcta5',
                    'zip_lookup', 'zip_lookup_all', 'zip_lookup_base', 'zip_state',
                    'zip_state_loc'
                }
                if name in postgis_tables:
                    return False
        return True

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives
    if conf_args.get("include_object") is None:
        conf_args["include_object"] = include_object

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

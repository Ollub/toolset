# Django/aiohttp toolset

Library with different python snippets.

## Content

* [How to install](#how_to_install)
* [Contribute](#contribute)
* **[Rest utils](#drf-tools)**
* [Tiny serializers](#tiny-serializers)
* [PrimaryKeyRelatedNestedField](#primarykeyrelatednestedfield)
* [BaseCustomErrors](#basecustomerrors)
* [Proxy errors](#proxy-errors)
* [ListErrorRepresentationSerializer](#listerrorrepresentationserializer)
* [Django soft delete](#django-soft-delete)
* [Retry decorator](#retry-decorator)
* [Event view](#event-view)
* **[Event bus](#event-bus-producers)**
* [Event bus Producers](#event-bus-producers)
* [Event bus Consumers](#event-bus-consumers)
* **[Api clients](#base-api-client)**
* [Base api client](#base-api-client)
* **[Testing](#testing)**


## How to install
* Add new source section to poetry `pyproject.toml`
    ```toml
    [[tool.poetry.source]]
    name = "gitlab"
    url = "https://gitlab.com/api/v4/projects/<project_id>/packages/pypi/simple/"
    ```

* Go to [gitlab token page](https://gitlab.com/profile/personal_access_tokens) 
and issue a "Personal access" token with `api` scope
* Run following commands in terminal
```shell script
poetry config repositories.gitlab https://gitlab.com/api/v4/projects/<project_id>/packages/pypi
poetry config http-basic.gitlab __token__ <token>
``` 
At last command `__token__` should be entered as is and then token value.
* And finally run
```shell script
poetry add toolset
or
poetry add toolset[django]
or
poetry add toolset[aiohttp]
```

#### Install into docker image
All tokens are available at group level, don't issue anything additionally.

See [aiohttp-template](https://gitlab.com/pik-pro/backend/aiohttp-template), specifically [this diff](https://gitlab.com/pik-pro/backend/aiohttp-template/-/compare/abdfc26f...2729076e) (omit kubernetes changes though).

## Contribute
1) Write new code
2) Write test for new code
3) **IMPORTANT** Bump version via poetry `poetry version patch|minor|major`
4) **IMPORTANT** Add all changes to `CHANGELOG.md`


## DRF tools
### Tiny serializers
`poetry add toolset[django]`

For get requests it's inefficient to use usual ModelSerializer. 
Replace it with `tiny` which doesn't weight a lot 
and doesn't use additional queryset/model validation.

```python
from toolset.drf.serializers import make_tiny
from app.serializers import MyModelSerializer


class MyModelViewSet(ModelViewSet):
    queryset = MyModel.objects.all()
    serializer = make_tiny(MyModelSerializer())
```

### PrimaryKeyRelatedNestedField

```python
from toolset.drf.serializers import PrimaryKeyRelatedNestedField

class MyModelSerializer(serializers.ModelSerializer):
    """Serializer for my model."""

    related_field = PrimaryKeyRelatedNestedField(
        RelatedModelNestedSerializer, queryset=RelatedModel.objects.all(), source="related_field",
    )
    
    class Meta:
        model = MyModel
```
`PrimaryKeyRelatedNestedField` useful when you want to send in response full nested data 
but receive only ids.

```python
# request
>>> request.patch('api/my-model/111', data={'related_field': 666})
# response
>>> r = request.get('url/my-model/111')
>>> r.json()
{'related_field': {'id': 666, 'name': 'I am groot', 'friends': ['Rocket']}}
``` 

### BaseCustomErrors

Overrides default APIException with 422 error_code instead of 400.

This is required to distinguish errors with JS client from business errors.
We cannot override `exceptions.ValidationError` directly, because DRF ignores
inheritance many times: https://stackoverflow.com/a/51567740

In settings.py add:

```python

SERVICE_NAME = "YOUR_SERVICE_NAME"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "toolset.drf.exceptions_utils.handlers.custom_exception_handler",
}

```
`SERVICE_NAME` will be added to every custom error's `default_code` like `SERVICE_NAME/YOU_CUSTOM_ERROR_NAME`

Than you can create and use your custom errors for your service for example like this:

```python
from toolset.drf.exceptions_utils import BaseCustomError

class ProtectedInstanceError(BaseCustomError):
    """Custom exception for handling on_delete=models.Protect."""

    default_detail = "Delete is unprocessable."
    default_code = "DELETE_PROTECTED"
```

#### Proxy errors
There is a proxy error which you can use to proxy errors from other services

```python
import requests
from toolset.drf.exceptions_utils import BaseProxyCustomError

class BGError(BaseProxyCustomError):
    # specify detail and code if you need to, but usually it's not necessary
    # default_detail = "Section is not int"
    # default_code = "BG/SECTION IS VERY BAD"

def call_bg():
    r = requests.post("bg_url", data={"section_id": 1})
    r_data = r.json()
    if "error" in r_data:
        raise BGError(detail=r_data["detail"], error_code=r_data["error_code"])
```

DRF will catch this error and handle it like usual service custom error, but will not add service name to error code.

### ListErrorRepresentationSerializer
Serializer to represent list of errors in Swagger.

Usage:

```python
from toolset.drf.exceptions_utils import ListErrorRepresentationSerializer

@swagger_auto_schema(
    responses={
        status.HTTP_200_OK: WhateverSerializer(),
        status.HTTP_422_UNPROCESSABLE_ENTITY: ListErrorRepresentationSerializer(
            [ProtectedInstanceError],
        ),
    },
)
```

### Django soft delete
Library provides model and migration functions to soft delete.

You should create a separate django-app and own model

```python
# soft_delete_app/models.py
from toolset.django.soft_delete.models import SoftDeletableABC

class SoftDeletableModel(SoftDeletableABC):
    """Abstract class for soft deleted models."""

    class Meta:
        # IMPORTANT, this model should be abstract
        abstract = True
```

After that you should perform four operations
1) Modify `settings.py`
```python
INSTALLED_APPS = (
    ...,
    'soft_delete_app',
)

DATABASES = {
    "default": {
        ...
    },
}
DATABASES["deleted"] = {**DATABASES["default"]}
DATABASES["deleted"]["OPTIONS"] = {"options": "-c search_path=deleted"}
# router needed for proper migrations
DATABASE_ROUTERS = ["toolset.django.soft_delete.db_manager.SoftDeleteDBRouter"]
```
2) Create empty migration for app `./manage.py makemigrations soft_delete_app --empty`

```python
# 0001_initial.py
# Generated by Django 3.0.4 on 2020-03-26 15:32
import os

from django.db import migrations

from toolset.django.soft_delete.sql import soft_delete_functions_sql


db_user = os.environ.get("DB_USER")


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            f"""
            create schema if not exists deleted;
            GRANT ALL ON SCHEMA deleted TO "{db_user}";
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(soft_delete_functions_sql, reverse_sql=migrations.RunSQL.noop),
    ]
```

3) Inherit models you want to store from `SoftDeletableModel` and just run `./manage.py makemigrations`.
Migration with copy of models should appear in `soft_delete_app/migrations`.

Important note, `SoftDeletableModel` should be first parent.

4) IMPORTANT!!! You need to set triggers for these models. Run again `./manage.py makemigrations soft_delete_app --empty`

```python
# 0003_auto
# Generated by Django 3.0.4 on 2020-03-27 10:12

from django.db import migrations
from toolset.django.soft_delete.sql import get_soft_delete_sql_triggers

default_triggers = []
deleted_triggers = []

# Note, we can't use Model and extract db_name here
# so you must tell explicitly which db_table should processed
for table_name in ("table_for_model1", "table_for_model2"):
    def_t, del_t = get_soft_delete_sql_triggers(table_name)
    default_triggers.extend(def_t)
    deleted_triggers.extend(del_t)


class Migration(migrations.Migration):

    dependencies = [
        ('soft_deleted', '0002_deleted_models'),
    ]

    # IMPORTANT!!! using_db kwarg is necessary here
    # otherwise all trigger sqls will run on every schema 
    operations = [
        migrations.RunSQL(default_triggers, reverse_sql=migrations.RunSQL.noop, hints={"using_db": "default"}),
        migrations.RunSQL(deleted_triggers, reverse_sql=migrations.RunSQL.noop, hints={"using_db": "deleted"}),
    ]
```

5) Important, but optional. 
If you inherit old models which has a bunch of migrations already, 
it's possible that order of fields in `deleted` migration will not the same as original.
This is because django create migration looking for order of model attributes.
You should manually check `deleted` migrations and re order fields to match order from db.

That's all, you've got soft_deleted schema.

##### Important

Remember to repeat fourth step every time you inherit your models from `SoftDeletableModel`

##### Soft Delete notes
* To migrate you need to edit `bin/migrate.sh`
```shell script
python manage.py migrate
python manage.py migrate --database=deleted
```
* For every data migration you already have you should add hints. This way they will not execute in soft delete
```python
migrations.RunSQL(..., hints={"using_db": "default"})
```
* Next data migrations you create **will** execute in soft delete schema unless you specify hints.
* It is useful to modify settings for tests somewhere in `conftest.py`
```python
@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    del settings.DATABASES[settings.SOFT_DELETE_DB]
    settings.INSTALLED_APPS = [
        app for app in settings.INSTALLED_APPS if app != "{SERVICE_NAME}.soft_deleted"
    ]
```

### Retry decorator

Retry decorator tries to call decorated function given number of times. It will sleep for `wait_time_seconds`
between attempts. Each time `wait_time_seconds` will be multiplied by `backoff` to wait a bit longer (or shorter
if you will). You should also pass specific exception(s), because decorated function will be called again only 
if specified exception(s) occur. 

There are async and traditional versions.

Example:

```python
from toolset.decorators import retry


@retry(ValueError, TypeError, attempts=3, wait_time_seconds=0.5, backoff=2)
def your_func():
    ...
```

The same with async version:

```python
from toolset.decorators import aio_retry

@aio_retry(ValueError, TypeError, attempts=3, wait_time_seconds=0.5, backoff=2)
def your_func():
    ...
```

### Event bus Producers

#### Sync version (Django)
**Requirements**:
* Define `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_HOST`, `RABBITMQ_PORT` env variables
* Optionally define `RABBITMQ_BLOCKED_CONNECTION_TIMEOUT` (int) env variable
* Enable `pikrpo` logger in django settings
```python
LOGGING = {
    ...: ...,
    "loggers": {
        ...: ...,
        "toolset": {"level": LOG_LEVEL, "handlers": ["json"], "propagate": False},
    },
}
```

**Usage**

```python
#############
# producer.py

from toolset.event_bus.django import BaseProducer

class HrmProducer(BaseProducer):
    exchange = "hrm"

    routing_key = "key"


#########
# view.py

producer = HrmProducer()
producer.publish(producer.routing_key, {"user_id": 1})
producer.close()
# or
with HrmProducer() as producer:
    producer.publish(producer.routing_key, {"user_id": 1})
    producer.publish(producer.routing_key, {"user_id": 2})

# instead of defaults one can pass params manually
from toolset.event_bus.django.producers import NON_PERSISTENT_DELIVERY_MODE, PERSISTENT_DELIVERY_MODE
producer = HrmProducer(
    url_params=pika.URLParameters("amqp://user:12345@localhost:5762/?blocked_connection_timeout=60"),
    pika_props=pika.BasicProperties(
        content_type="application/json", delivery_mode=NON_PERSISTENT_DELIVERY_MODE,
    )
)
```

**Tests**

Here are some mocks to use in tests

```python
# conftest.py

import pika

from toolset.event_bus.django.producers import ConnectionMock

pika.BlockingConnection = ConnectionMock
```

#### Async version (aiohttp)

**Usage**

```python
#############
# setup.py

from toolset.event_bus.aio import BaseProducer, get_rabbit_channel_pool, get_rabbit_connection_pool

class AuthProducer(BaseProducer):
    exchange = "auth"


async def setup_rabbit(app: AioApp) -> None:
    """Setup rabbit connection."""
    rabbit_connection_pool: Pool[aio_pika.Connection] = await get_rabbit_connection_pool(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        user=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        max_size=2,
    )
    rabbit_channel_pool: Pool[aio_pika.Channel] = await get_rabbit_channel_pool(
        pool=rabbit_connection_pool,
        max_size=2,
    )
    app.producer = AuthProducer(
        connection_pool=rabbit_connection_pool, channel_pool=rabbit_channel_pool,
    )


async def shutdown_pools(app: AioApp) -> None:
    """Properly shutdown rabbit pool."""
    await app.producer.teardown()


#########
# view.py

async def view(request):
    await request.app.producer.publish('routing_key', {'data': {'id': 1}})
```

**Tests**

Here are some mocks to use in tests

```python
# client_fixtures.py
@pytest.fixture()
async def client(aiohttp_client, app):
    """Aiohttp client."""
    client = await aiohttp_client(app)
    client.app.producer = asynctest.create_autospec(AuthProducer)
    yield client

# OR
from toolset.event_bus.aio import BaseProducerMock

@pytest.fixture()
async def client(aiohttp_client, app):
    """Aiohttp client."""
    client = await aiohttp_client(app)
    client.app.producer = BaseProducerMock()
    yield client
```


### Event bus Consumers

#### Async version (aiohttp)


**Requirements**:
* Define `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_HOST`, `RABBITMQ_PORT` env variables

Or
* Override `host`, `port`, `user`, `password` attributes of consumer


**Base consumer Usage**

```python
#############
# consume.py

import asyncio
from toolset.event_bus.aio import BaseConsumer
from my_service.setup import get_app

QUEUE_NAME = "my_service:some_logic"

async def handler(
    message_body, routing_key, app
):
    """Handler"""
    msg = message_body["data"]


async def start_consuming_in_ctx() -> None:
    """Register consumer and start consuming."""

    app = get_app()

    async with BaseConsumer(QUEUE_NAME) as consumer:
        await consumer.consume(
           handler, "hrm", ["user.updated", "user.created"], app=app,
    )

# or

async def start_consuming() -> None:
    """Register consumer and start consuming."""

    app = get_app()
    
    consumer = BaseConsumer(QUEUE_NAME)
    await consumer.init_connection()
    try:
        consumer.consume(...)
    except:
        await consumer.close_connection()


def main():
    asyncio.run(start_consuming())


```

If you need to bind queue with several exchanges you can use .bind() method


```python

consumer = BaseConsumer(QUEUE_NAME)
consumer.bind("foo", ["routing_key1", "routing_key2"])
consumer.bind("bar", ["routing_key3"])
await consumer.init_connection()
await consumer.consume()

```

**BaseGarbageConsumer**

Work principals are described in [miro diagram](https://miro.com/app/board/o9J_kjpHg-0=/)


**Usage**

```python
#############
# consume.py

import asyncio
from toolset.event_bus.aio import BaseGarbageConsumer
from my_service.setup import get_app

QUEUE_NAME = "my_service:some_logic"


class GarbageConsumer(BaseGarbageConsumer):
    
    exchange_name = "my_service"


async def handler(
    message_body, routing_key, app
):
    """Handler"""
    # do logic


async def start_consuming() -> None:
    """Register consumer and start consuming."""

    app = get_app()

    async with GarbageConsumer(QUEUE_NAME) as consumer:
        await consumer.consume(
            handler, "hrm", ["user.updated", "user.created"], app=app,
    )


def main():
    asyncio.run(start_consuming())

###

```
#### Sync version (django)

Define `RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT` environment variables

Enable `pikrpo` logger in django settings
```python
LOGGING = {
    ...: ...,
    "loggers": {
        ...: ...,
        "toolset": {"level": LOG_LEVEL, "handlers": ["json"], "propagate": False},
    },
}
```

**Base logic to init and consume logic**

```python
from toolset.event_bus.django import BaseConsumer
from toolset.typing_helpers import JSON

QUEUE_NAME = "my_service:some_logic"


def callback(routing_key: str, message: JSON):
    # do some logic with message

def logic():
    
    rabbit_consumer = BaseConsumer(QUEUE_NAME, callback)
    
    try:
        rabbit_consumer.start_consuming(
            "hrm", ["user.updated", "user.created"],
        )
    
    except Exception as exc:
        logger.error("Consumer closed unexpectedly", exc=exc)
    
    finally:
        logger.info("Consumer terminate")
        rabbit_consumer.close()

```

Or with context manager

```python
    with BaseConsumer(QUEUE_NAME, callback) as consumer:
        rabbit_consumer.start_consuming(
            "hrm", ["user.updated", "user.created"],
        )
```

In some cases you are able to provide the custom connection properties:

```python
from toolset.event_bus.django.base import NON_PERSISTENT_DELIVERY_MODE, PERSISTENT_DELIVERY_MODE

consumer = BaseConsumer(
    QUEUE_NAME, 
    callback,
    url_params=pika.URLParameters("amqp://user:12345@localhost:5762/?blocked_connection_timeout=60"),
    pika_props=pika.BasicProperties(
        content_type="application/json", delivery_mode=NON_PERSISTENT_DELIVERY_MODE,
    )
)
```


Also you are able to bind routing keys with several exchanges:

```python

consumer = BaseConsumer(QUEUE_NAME, callback)
consumer.bind("foo", ["routing_key1", "routing_key2"])
consumer.bind("bar", ["routing_key3"])
consumer.start_consuming()

```

**Garbage consumer:**

Define subclass GarbageConsumer

```python
from toolset.event_bus.django import GarbageConsumer

class MyGarbageConsumer(GarbageConsumer):

    exchange_name = "my_service"

```

Usage:
```python

def callback(routing_key: str, message: JSON):
    # do some logic with message 
    # or raise an exception to move the message to the garbage queue

def logic():

     with MyGarbageConsumer(
            QUEUE_NAME, callback, store_failed=True,
        ) as consumer:

            consumer.start_consuming(
                "hrm", ["user.updated"],
            )

```

### Base api client
Define `SERVICE_SECRET` env variable. 
`BaseApiClient` propagate service secret headers to request (or injecting if headers passed with request).
#### Sync (django)
Same interface as `requests`

```python
from toolset.sync.base_api_client import BaseApiClient

class ServiceApiClient(BaseApiClient):

    service_name = "hrm"

class GeometriesApiClient(ServiceApiClient):

    def get_sections(self, section_ids: tp.List[int]):
        r = self.get("pik.pro/geometries/sections", params={"id": section_ids})
        r.raise_for_status()
        return r.json()
```

#### Async (aiohttp)
Same interface as `aiohttp.ClientSession`

```python
from toolset.aio.base_api_client import BaseApiClient

class ServiceApiClient(BaseApiClient):

    service_name = "auth"

class GeometriesApiClient(ServiceApiClient):

    async def get_sections(self, section_ids: tp.List[int]):
        r = await self.get("pik.pro/geometries/sections", params=self.make_params({"id": section_ids}))
        r.raise_for_status()
        return await r.json()
```

Note that aio client has method `make_params` which can convert usual dict-style params to tuple-style.


### Event view
Example:

```python
from toolset.django.event_view import get_event_view

class EventsSerializer(serializers.Serializer):
    object__created = ObjectsCreatedEventSerializer()
    object__updated = ObjectsUpdatedEventSerializer()

urlpatterns.append(
    url("api/v1/event-system-entities", get_event_view(EventsSerializer))
)
```

## Testing

### assert_matches()
Rewritten function from [matchlib](https://github.com/qweeze/matchlib/blob/master/matchlib/main.py)

Matches a given object against another which can contain an Ellipsis (`...`)

Returns True if object match or match partially with ellipsis.
Otherwise, raises an error with proper message what do not match.

**Usage:**

```python
from toolset.testing.matching import assert_matches

# Example 1:
assert_matches({1, 2, 3}, {1, 2, ...})  # True

# Example 2:
d1 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Flipper"}}
d2 = {"cats": {"Fluffy", "Snowball"}, "dogs": {"Rex", "Gigi"}}

assert_matches(d1, d2)
# AssertionError: Dicts have different value for key: 'dogs'. Cause: Sets are unequal.
# Partial set has extra elements: {'Gigi'}.
# Original set has extra elements: {'Flipper'}.
```
"""Stand-ins for Home Assistant, voluptuous and pyyardian, just enough to import and run the integration's code.

Import this module before anything from custom_components.yardian_local. It registers small fake modules in
sys.modules, so the tests run on plain Python with nothing installed, as every other check does. The stand-ins
copy the behaviour the integration relies on (a schema that validates, a coordinator that holds ``data``, an
entity's ``available``), not Home Assistant's whole API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True  # keep __pycache__ out of custom_components/ (and out of the zip build_package.py makes)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules.get(parent) or module(parent), child, mod)
    return mod


class Anything:
    """Any attribute is a fresh string, so enum-like constants (UnitOfTime.MINUTES, Platform.SWITCH) just work."""

    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        return f"{self._name}.{attr}"


# ---------------------------------------------------------------- voluptuous (the parts the schemas use)


class Invalid(Exception):
    pass


class _Marker:
    def __init__(self, key, default=None):
        self.key = key

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return getattr(other, "key", other) == self.key


class Required(_Marker):
    pass


class Optional(_Marker):
    pass


def _validate(validator, value):
    if isinstance(validator, list):
        if not isinstance(value, list):
            raise Invalid("expected a list")
        return [_validate(validator[0], item) for item in value]
    if isinstance(validator, Schema):
        return validator(value)
    return validator(value)


class Schema:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, data):
        if not isinstance(self.schema, dict):
            return _validate(self.schema, data)
        if not isinstance(data, dict):
            raise Invalid("expected a dictionary")
        out = {}
        for marker, validator in self.schema.items():
            if marker.key in data:
                out[marker.key] = _validate(validator, data[marker.key])
            elif isinstance(marker, Required):
                raise Invalid(f"required key not provided: {marker.key}")
        extra = set(data) - {marker.key for marker in self.schema}
        if extra:
            raise Invalid(f"extra keys not allowed: {extra}")
        return out


def All(*validators):
    def check(value):
        for validator in validators:
            value = _validate(validator, value)
        return value

    return check


def Coerce(kind):
    def check(value):
        try:
            return kind(value)
        except (TypeError, ValueError) as err:
            raise Invalid(str(err)) from err

    return check


def Range(min=None, max=None):
    def check(value):
        if (min is not None and value < min) or (max is not None and value > max):
            raise Invalid("out of range")
        return value

    return check


module(
    "voluptuous",
    Invalid=Invalid,
    Schema=Schema,
    Required=Required,
    Optional=Optional,
    All=All,
    Coerce=Coerce,
    Range=Range,
)


def ensure_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def string(value):
    if value is None or isinstance(value, dict | list):
        raise Invalid("expected a string")
    return str(value)


# ---------------------------------------------------------------- Home Assistant


class HomeAssistantError(Exception):
    def __init__(self, *args, translation_domain=None, translation_key=None, translation_placeholders=None):
        super().__init__(*args or [translation_key])
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class ServiceValidationError(HomeAssistantError):
    pass


class ConfigEntryAuthFailed(HomeAssistantError):
    pass


class ConfigEntryNotReady(HomeAssistantError):
    pass


class UpdateFailed(HomeAssistantError):
    pass


class ServiceCall:
    def __init__(self, data):
        self.data = data


class Services:
    """hass.services: a registry of async handlers, and a log of every call made through it."""

    def __init__(self):
        self.handlers = {}
        self.schemas = {}
        self.calls = []

    def async_register(self, domain, name, handler, schema=None):
        self.handlers[(domain, name)] = handler
        self.schemas[(domain, name)] = schema

    def has_service(self, domain, name):
        return (domain.lower(), name.lower()) in self.handlers

    async def async_call(self, domain, name, data, blocking=False):
        self.calls.append((domain, name, data))
        handler = self.handlers[(domain, name)]
        result = handler(ServiceCall(data))
        if hasattr(result, "__await__"):
            await result

    async def call_validated(self, domain, name, data):
        """Call like Home Assistant does: the schema first (raising Invalid), then the handler."""
        schema = self.schemas[(domain, name)]
        await self.handlers[(domain, name)](ServiceCall(schema(data) if schema else data))


class HomeAssistant:
    def __init__(self):
        self.services = Services()


class Store:
    """helpers.storage.Store, kept in memory: ``saved`` is what async_load returns."""

    def __init__(self, hass, version, key):
        self.saved = None
        self.delayed = []

    async def async_load(self):
        return self.saved

    async def async_save(self, data):
        self.saved = data

    def async_delay_save(self, func, delay):
        self.delayed.append(func)


class DataUpdateCoordinator:
    def __init__(self, hass, logger, config_entry=None, name=None, update_interval=None):
        self.hass = hass
        self.config_entry = config_entry
        self.data = None
        self.last_update_success = True

    def __class_getitem__(cls, item):
        return cls

    async def async_refresh(self):
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except UpdateFailed:
            self.last_update_success = False

    def async_update_listeners(self):
        pass

    async def async_request_refresh(self):
        await self.async_refresh()


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        pass


class Entity:
    pass


class NumberEntity(Entity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100

    @property
    def native_min_value(self):
        return self._attr_native_min_value

    @property
    def native_max_value(self):
        return self._attr_native_max_value


class RestoreNumber(NumberEntity):
    last_number_data = None  # set by a test: what Home Assistant restored

    async def async_get_last_number_data(self):
        return self.last_number_data


def parse_datetime(value):
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def callback(func):
    return func


REDACTED = "**REDACTED**"
anything = {name: Anything(name) for name in ("Platform", "EntityCategory", "UnitOfTime", "UnitOfVolume")}
anything["UnitOfVolumeFlowRate"] = Anything("UnitOfVolumeFlowRate")


class SensorDeviceClass(StrEnum):
    TIMESTAMP = "timestamp"
    DURATION = "duration"
    WATER = "water"


module("homeassistant")
module("homeassistant.core", HomeAssistant=HomeAssistant, ServiceCall=ServiceCall, callback=callback)
module(
    "homeassistant.const",
    CONF_ACCESS_TOKEN="access_token",
    CONF_HOST="host",
    **anything,
)
module(
    "homeassistant.exceptions",
    HomeAssistantError=HomeAssistantError,
    ServiceValidationError=ServiceValidationError,
    ConfigEntryAuthFailed=ConfigEntryAuthFailed,
    ConfigEntryNotReady=ConfigEntryNotReady,
)
module(
    "homeassistant.config_entries",
    ConfigEntry=type("ConfigEntry", (), {"__class_getitem__": classmethod(lambda c, i: c)}),
)
module("homeassistant.helpers")
module(
    "homeassistant.helpers.config_validation",
    ensure_list=ensure_list,
    string=string,
    config_entry_only_config_schema=lambda domain: None,
)
module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
module("homeassistant.helpers.typing", ConfigType=dict)
module("homeassistant.helpers.device_registry", DeviceInfo=dict)
module("homeassistant.helpers.storage", Store=Store)
module(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=DataUpdateCoordinator,
    UpdateFailed=UpdateFailed,
    CoordinatorEntity=CoordinatorEntity,
)
module("homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object)
module("homeassistant.util")
module(
    "homeassistant.util.dt",
    parse_datetime=parse_datetime,
    utcnow=lambda: datetime.now(UTC),
)
module("homeassistant.components")
module("homeassistant.components.diagnostics", REDACTED=REDACTED)
module("homeassistant.components.switch", SwitchEntity=Entity)
module(
    "homeassistant.components.sensor",
    SensorEntity=Entity,
    SensorDeviceClass=SensorDeviceClass,
    SensorStateClass=Anything("SensorStateClass"),
)
module(
    "homeassistant.components.number",
    RestoreNumber=RestoreNumber,
    NumberDeviceClass=Anything("NumberDeviceClass"),
    NumberMode=Anything("NumberMode"),
)

# ---------------------------------------------------------------- pyyardian


class NotAuthorizedException(Exception):
    pass


class NetworkException(Exception):
    pass


class YardianDeviceState:
    def __init__(self, zones, active_zones):
        self.zones = zones
        self.active_zones = active_zones


class FakeClient:
    """A controller that answers with whatever the test puts in ``zones``, ``active`` and ``oper``."""

    def __init__(self, zones=None, active=(), oper=None):
        self.zones = zones if zones is not None else [["Front", 1], ["Back", 1]]
        self.active = active
        self.oper = oper if oper is not None else {}

    async def fetch_device_state(self):
        return YardianDeviceState(self.zones, self.active)

    async def fetch_oper_info(self):
        return self.oper


module(
    "pyyardian",
    AsyncYardianClient=FakeClient,
    NotAuthorizedException=NotAuthorizedException,
    NetworkException=NetworkException,
)


class FakeEntry:
    """A config entry for one controller."""

    def __init__(self, units="metric"):
        self.entry_id = "entry1"
        self.title = "Yardian"
        self.data = {"yid": "yid1", "units": units, "host": "192.0.2.10", "access_token": "secret"}
        self.runtime_data = None


__all__ = ["FakeClient", "FakeEntry", "HomeAssistant", "Invalid", "ServiceCall", "timedelta"]

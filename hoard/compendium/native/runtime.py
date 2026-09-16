"""Interpreter for compiled RPG Companion calculations, mechanics, and effects."""

from __future__ import annotations

import random
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

SUPPORTED_NATIVE_VIEW_TYPES = frozenset(
    {
        "avatar",
        "avatarSection",
        "button",
        "checkbox",
        "chip",
        "collapsible",
        "composite",
        "diffText",
        "divider",
        "icon",
        "listItem",
        "list",
        "menuButton",
        "popUpButton",
        "resource",
        "resourceArray",
        "resourceSection",
        "section",
        "select",
        "selectResources",
        "spacer",
        "stat",
        "text",
        "ticker",
        "viewPager",
    }
)


class NativeRuntimeError(ValueError):
    """Raised when a native contract cannot be evaluated safely."""


@dataclass
class NativeScope:
    """Values visible while evaluating one native definition."""

    values: dict[str, Any]
    character: dict[str, Any] | None = None
    parent: dict[str, Any] | None = None
    global_values: dict[str, Any] = field(default_factory=dict)
    view: dict[str, Any] = field(default_factory=dict)
    locals: dict[str, Any] = field(default_factory=dict)

    def child(self, **locals: Any) -> NativeScope:
        """Return a scope with additional lambda-local bindings."""
        return NativeScope(
            values=self.values,
            character=self.character,
            parent=self.parent,
            global_values=self.global_values,
            view=self.view,
            locals={**self.locals, **locals},
        )


@dataclass
class NativeExecution:
    """Observable result of processing one native event."""

    state: dict[str, Any]
    fired_events: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    interface_actions: list[dict[str, Any]] = field(default_factory=list)
    delayed_effects: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    unsupported: list[dict[str, Any]] = field(default_factory=list)


class NativeEvaluator:
    """Evaluate compiled calculation nodes with lazy calculated-stat lookup."""

    def __init__(
        self,
        definition: dict[str, Any],
        values: dict[str, Any],
        *,
        random_source: random.Random | None = None,
        resource_lookup: Callable[[str, str], dict[str, Any] | None] | None = None,
        character_evaluator: NativeEvaluator | None = None,
    ) -> None:
        self.definition = definition
        self.values = values
        self.random = random_source or random.Random()
        self.resource_lookup = resource_lookup
        self.character_evaluator = character_evaluator
        self.stat_definitions = {
            stat["id"]: stat
            for stat in definition.get("character_stats", definition.get("stats", []))
            if isinstance(stat, dict) and isinstance(stat.get("id"), str)
        }
        self.enumerated_types = {
            item["id"]: item
            for item in definition.get("enumerated_types", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        self.cache: dict[str, Any] = {}
        self.evaluating: set[str] = set()

    def default_state(self) -> dict[str, Any]:
        """Return defaults for all native base stats, overlaid by stored values."""
        state = {
            identifier: deepcopy(definition.get("default_value"))
            for identifier, definition in self.stat_definitions.items()
            if definition.get("type") == "base"
        }
        state.update(deepcopy(self.values))
        return state

    def stat(self, identifier: str, scope: NativeScope) -> Any:
        """Resolve a native stat or scoped path, including optional path markers."""
        if identifier.startswith("$") or "." in identifier:
            return self.resolve_path(identifier, scope)
        if identifier in scope.values:
            return unwrap_native_value(scope.values[identifier])
        if identifier in self.cache:
            return self.cache[identifier]
        definition = self.stat_definitions.get(identifier)
        if definition is None:
            return None
        if definition.get("type") == "base":
            return deepcopy(definition.get("default_value"))
        if identifier in self.evaluating:
            raise NativeRuntimeError(f"Calculated stat cycle detected at {identifier}.")
        self.evaluating.add(identifier)
        try:
            value = self.evaluate(definition.get("components"), scope)
            self.cache[identifier] = value
            return value
        finally:
            self.evaluating.remove(identifier)

    def resolve_path(self, path: str, scope: NativeScope) -> Any:
        """Resolve dotted resource, character, global, view, and lambda paths."""
        parts = path.replace("?.", ".").split(".")
        first = parts.pop(0)
        first = first.rstrip("?")
        roots = {
            "$character": scope.character,
            "$parent": scope.parent,
            "$g": scope.global_values,
            "$view": scope.view,
        }
        if first in roots:
            current = roots[first]
        elif first.startswith("$"):
            current = scope.locals.get(first, scope.global_values.get(first))
        else:
            current = self.stat(first.rstrip("?"), scope)
        for index, raw_part in enumerate(parts):
            part = raw_part.rstrip("?")
            if current is None:
                return None
            if (
                isinstance(current, dict)
                and part in {"stats", "value"}
                and part in current
            ):
                current = current[part]
                continue
            current = unwrap_native_value(current)
            if isinstance(current, dict):
                stats = current.get("stats")
                if isinstance(stats, dict) and part in stats:
                    current = stats.get(part)
                elif (
                    isinstance(current.get("resource_id"), str)
                    and isinstance(stats, dict)
                ):
                    current = self.stat_from_resource(part, current, scope)
                elif (
                    first == "$character"
                    and index == 0
                    and part not in current
                    and self.character_evaluator is not None
                ):
                    character_scope = NativeScope(
                        values=scope.character or {},
                        character=scope.character,
                        global_values=scope.global_values,
                        view=scope.view,
                        locals=scope.locals,
                    )
                    current = self.character_evaluator.stat(part, character_scope)
                else:
                    current = current.get(part)
                continue
            if isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
                continue
            return None
        return unwrap_native_value(current)

    def evaluate(self, node: Any, scope: NativeScope | None = None) -> Any:
        """Evaluate one compiled expression node."""
        scope = scope or NativeScope(values=self.values, character=self.values)
        if isinstance(node, list):
            return [self.evaluate(value, scope) for value in node]
        if not isinstance(node, dict):
            return node
        node_type = node.get("type")
        if not isinstance(node_type, str):
            return {key: self.evaluate(value, scope) for key, value in node.items()}
        handler = getattr(self, f"evaluate_{node_type}", None)
        if handler is None:
            raise NativeRuntimeError(f"Unsupported calculation type: {node_type}.")
        return handler(node, scope)

    def evaluate_constant(self, node: dict[str, Any], scope: NativeScope) -> Any:
        return deepcopy(node.get("value"))

    def evaluate_stat(self, node: dict[str, Any], scope: NativeScope) -> Any:
        identifier = node.get("stat")
        if not isinstance(identifier, str):
            return None
        resource_node = node.get("for_resource")
        if resource_node is not None:
            resource = self.evaluate(resource_node, scope)
            return self.stat_from_resource(identifier, resource, scope)
        if node.get("ignore_cache"):
            self.cache.pop(identifier, None)
        return self.stat(identifier, scope)

    def stat_from_resource(
        self,
        identifier: str,
        resource: Any,
        scope: NativeScope,
    ) -> Any:
        """Evaluate a stat against the explicitly supplied native resource."""
        resource = unwrap_native_value(resource)
        if not isinstance(resource, dict):
            return None
        stats = resource.get("stats")
        if not isinstance(stats, dict):
            return None
        resource_id = resource.get("resource_id")
        root = self.character_evaluator or self
        definition = next(
            (
                candidate
                for candidate in root.definition.get("resources", [])
                if isinstance(candidate, dict) and candidate.get("id") == resource_id
            ),
            {},
        )
        evaluator = NativeEvaluator(
            definition,
            stats,
            random_source=self.random,
            character_evaluator=root,
        )
        resource_scope = NativeScope(
            values=stats,
            character=scope.character,
            parent=scope.parent,
            global_values=scope.global_values,
            view=scope.view,
            locals=scope.locals,
        )
        return evaluator.stat(identifier, resource_scope)

    def evaluate_metaStat(self, node: dict[str, Any], scope: NativeScope) -> Any:
        identifier = self.evaluate(node.get("meta_stat"), scope)
        return self.stat(identifier, scope) if isinstance(identifier, str) else None

    def evaluate_list(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        components = node.get("components", [])
        return self.evaluate(components, scope) if isinstance(components, list) else []

    def evaluate_add(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        return sum(value or 0 for value in values)

    def evaluate_subtract(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        if not values:
            return 0
        return values[0] - sum(value or 0 for value in values[1:])

    def evaluate_multiply(self, node: dict[str, Any], scope: NativeScope) -> Any:
        result: int | float = 1
        for value in self.component_list(node, scope):
            result *= value or 0
        return result

    def evaluate_divide(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        if not values:
            return 0
        result = values[0]
        for value in values[1:]:
            if not value:
                return 0
            result /= value
        rounding = node.get("rounding_method")
        if rounding == "down":
            return int(result // 1)
        if rounding == "up":
            return int(-(-result // 1))
        if rounding in {"round", "nearest"}:
            return round(result)
        return result

    def evaluate_min(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        return min(values) if values else 0

    def evaluate_max(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        return max(values) if values else 0

    def evaluate_concat(self, node: dict[str, Any], scope: NativeScope) -> str:
        return "".join("" if value is None else str(value) for value in self.component_list(node, scope))

    def evaluate_and(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return all(bool(value) for value in self.component_list(node, scope))

    def evaluate_or(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return any(bool(value) for value in self.component_list(node, scope))

    def evaluate_not(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return not bool(self.evaluate(node.get("components"), scope))

    def evaluate_equals(self, node: dict[str, Any], scope: NativeScope) -> bool:
        values = self.component_list(node, scope)
        return all(left == right for left, right in zip(values, values[1:]))

    def evaluate_notEquals(self, node: dict[str, Any], scope: NativeScope) -> bool:
        values = self.component_list(node, scope)
        return all(left != right for left, right in zip(values, values[1:]))

    def evaluate_greaterThan(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.ordered_comparison(node, scope, lambda left, right: left > right)

    def evaluate_greaterThanEquals(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.ordered_comparison(node, scope, lambda left, right: left >= right)

    def evaluate_lessThan(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.ordered_comparison(node, scope, lambda left, right: left < right)

    def evaluate_lessThanEquals(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.ordered_comparison(node, scope, lambda left, right: left <= right)

    def evaluate_elevate(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        if not values:
            return 0
        result = values[0]
        for value in values[1:]:
            result **= value
        return result

    def evaluate_mod(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.component_list(node, scope)
        if not values:
            return 0
        result = values[0]
        for value in values[1:]:
            if not value:
                return 0
            result %= value
        rounding = node.get("rounding_method")
        if rounding == "down":
            return int(result // 1)
        if rounding == "up":
            return int(-(-result // 1))
        if rounding in {"round", "nearest"}:
            return round(result)
        return result

    def evaluate_negate(self, node: dict[str, Any], scope: NativeScope) -> Any:
        return -(self.evaluate(node.get("components"), scope) or 0)

    def evaluate_defaultIfNull(self, node: dict[str, Any], scope: NativeScope) -> Any:
        value = self.evaluate(node.get("components"), scope)
        return self.evaluate(node.get("default_components"), scope) if value is None else value

    def evaluate_when(self, node: dict[str, Any], scope: NativeScope) -> Any:
        for clause in node.get("clauses", []):
            if isinstance(clause, dict) and bool(self.evaluate(clause.get("condition"), scope)):
                return self.evaluate(clause.get("components"), scope)
        return None

    def evaluate_contains(self, node: dict[str, Any], scope: NativeScope) -> bool:
        haystack = self.evaluate(node.get("haystack"), scope)
        needle = self.evaluate(node.get("needle"), scope)
        try:
            return needle in haystack
        except TypeError:
            return False

    def evaluate_map(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        values = self.evaluate(node.get("components"), scope) or []
        key = node.get("map_value_key", "$mapValue")
        return [
            self.evaluate(node.get("mapper"), scope.child(**{str(key): value}))
            for value in values
        ]

    def evaluate_filter(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        values = self.evaluate(node.get("components"), scope) or []
        key = node.get("filter_value_key", "$filterValue")
        return [
            value
            for value in values
            if bool(self.evaluate(node.get("filter"), scope.child(**{str(key): value})))
        ]

    def evaluate_flatMap(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        return flatten(self.evaluate_map(node, scope))

    def evaluate_reduce(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = list(self.evaluate(node.get("components"), scope) or [])
        if not values:
            return None
        accumulator = values[0]
        accumulator_key = str(node.get("reduce_accumulator_key", "$reduceAccumulator"))
        value_key = str(node.get("reduce_value_key", "$reduceValue"))
        for value in values[1:]:
            child = scope.child(**{accumulator_key: accumulator, value_key: value})
            accumulator = self.evaluate(node.get("reducer"), child)
        return accumulator

    def evaluate_findFirst(self, node: dict[str, Any], scope: NativeScope) -> Any:
        values = self.evaluate(node.get("components"), scope) or []
        key = str(node.get("find_first_value_key", "$findFirstValue"))
        for value in values:
            child = scope.child(**{key: value})
            if bool(self.evaluate(node.get("filter"), child)):
                return value
        return None

    def evaluate_sortBy(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        values = list(self.evaluate(node.get("components"), scope) or [])
        selector = node.get("sort_by_selector")
        key = str(node.get("sort_by_value_key", "$sortByValue"))
        values.sort(
            key=lambda value: sortable_value(
                self.evaluate(selector, scope.child(**{key: value}))
            ),
            reverse=node.get("order") == "desc",
        )
        return values

    def evaluate_flatAppend(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        values = flatten(self.component_list(node, scope))
        return unique_values(values) if node.get("treat_as_set") else values

    def evaluate_append(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        if "list" in node:
            values = list(self.evaluate(node.get("list"), scope) or [])
            values.append(self.evaluate(node.get("item"), scope))
            return unique_values(values) if node.get("treat_as_set") else values
        return self.component_list(node, scope)

    def evaluate_length(self, node: dict[str, Any], scope: NativeScope) -> int:
        value = self.evaluate(node.get("components"), scope)
        return len(value) if value is not None else 0

    def evaluate_isEmpty(self, node: dict[str, Any], scope: NativeScope) -> bool:
        value = self.evaluate(node.get("components"), scope)
        return value is None or value == "" or value == [] or value == {}

    def evaluate_isNull(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.evaluate(node.get("components"), scope) is None

    def evaluate_notNull(self, node: dict[str, Any], scope: NativeScope) -> bool:
        return self.evaluate(node.get("components"), scope) is not None

    def evaluate_defined(self, node: dict[str, Any], scope: NativeScope) -> bool:
        identifier = node.get("stat")
        return isinstance(identifier, str) and self.resolve_path(identifier, scope) is not None

    def evaluate_joinToString(self, node: dict[str, Any], scope: NativeScope) -> str:
        values = self.evaluate(node.get("components"), scope) or []
        return str(node.get("separator", "")).join(str(value) for value in values)

    def evaluate_replace(self, node: dict[str, Any], scope: NativeScope) -> str:
        value = self.evaluate(node.get("string"), scope)
        occurrence = self.evaluate(node.get("occurrence"), scope)
        replacement = self.evaluate(node.get("replace"), scope)
        return str(value or "").replace(str(occurrence or ""), str(replacement or ""))

    def evaluate_split(self, node: dict[str, Any], scope: NativeScope) -> list[str]:
        value = self.evaluate(node.get("components"), scope)
        separator = self.evaluate(node.get("separator"), scope) if isinstance(node.get("separator"), dict) else node.get("separator")
        return re.split(str(separator), str(value or "")) if separator not in {None, ""} else list(str(value or ""))

    def evaluate_trim(self, node: dict[str, Any], scope: NativeScope) -> str:
        return str(self.evaluate(node.get("components"), scope) or "").strip()

    def evaluate_toLowerCase(self, node: dict[str, Any], scope: NativeScope) -> str:
        return str(self.evaluate(node.get("components"), scope) or "").lower()

    def evaluate_toUpperCase(self, node: dict[str, Any], scope: NativeScope) -> str:
        return str(self.evaluate(node.get("components"), scope) or "").upper()

    def evaluate_toNum(self, node: dict[str, Any], scope: NativeScope) -> int | float:
        value = self.evaluate(node.get("components"), scope)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0
        return int(number) if number.is_integer() else number

    def evaluate_toSignedString(self, node: dict[str, Any], scope: NativeScope) -> str:
        value = self.evaluate(node.get("components"), scope) or 0
        return f"+{value}" if value >= 0 else str(value)

    def evaluate_date(self, node: dict[str, Any], scope: NativeScope) -> str:
        value = self.evaluate(node.get("components"), scope)
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value
        return value.strftime("%b %d, %Y") if isinstance(value, datetime) else ""

    def evaluate_enumeratedName(self, node: dict[str, Any], scope: NativeScope) -> str:
        return self.enumerated_value(node, scope, "name")

    def evaluate_enumeratedAbbreviation(self, node: dict[str, Any], scope: NativeScope) -> str:
        return self.enumerated_value(node, scope, "abbreviation")

    def evaluate_roll(self, node: dict[str, Any], scope: NativeScope) -> int:
        if "formula" in node:
            formula = self.evaluate(node.get("formula"), scope)
            return roll_formula(str(formula or "0"), self.random)
        amount = int(self.evaluate(node.get("dice_amount"), scope) or node.get("dice_amount") or 1)
        dice = self.evaluate(node.get("dice_type"), scope) or node.get("dice_type") or "d20"
        match = re.search(r"(\d+)$", str(dice))
        sides = int(match.group(1)) if match else 20
        return sum(self.random.randint(1, sides) for unused in range(max(0, amount)))

    def evaluate_copyResource(self, node: dict[str, Any], scope: NativeScope) -> Any:
        resource = deepcopy(self.evaluate(node.get("components"), scope))
        if not node.get("preserve_ids", False):
            replace_resource_identifier(resource)
        return resource

    def evaluate_createChip(self, node: dict[str, Any], scope: NativeScope) -> dict[str, Any]:
        return {
            key: self.evaluate(value, scope) if isinstance(value, dict) else deepcopy(value)
            for key, value in node.items()
            if key != "type"
        }

    def evaluate_rollable(self, node: dict[str, Any], scope: NativeScope) -> dict[str, Any]:
        return {
            "formulas": node.get("formulas"),
            "text": node.get("text"),
        }

    def evaluate_eventName(self, node: dict[str, Any], scope: NativeScope) -> str:
        event_name = node.get("event_name", "")
        resource = (
            self.evaluate(node.get("for_resource"), scope)
            if node.get("for_resource") is not None
            else scope.values
        )
        identifier = native_resource_identifier(resource)
        return decorate_event_name(str(event_name), identifier)

    def enumerated_value(self, node: dict[str, Any], scope: NativeScope, field: str) -> str:
        type_id = node.get("enumerated_type")
        option_id = self.evaluate(node.get("id"), scope) if isinstance(node.get("id"), dict) else node.get("id")
        definition = self.enumerated_types.get(type_id, {})
        options = definition.get(
            "types",
            definition.get("options", definition.get("values", [])),
        )
        for option in options if isinstance(options, list) else []:
            if isinstance(option, dict) and option.get("id", option.get("value")) == option_id:
                value = option.get(field, option.get("name", option_id))
                return str(value or "")
        return str(option_id or "")

    def component_list(self, node: dict[str, Any], scope: NativeScope) -> list[Any]:
        value = self.evaluate(node.get("components"), scope)
        return value if isinstance(value, list) else [value]

    def comparison_values(self, node: dict[str, Any], scope: NativeScope) -> tuple[Any, Any]:
        values = self.component_list(node, scope)
        if len(values) >= 2:
            return values[0], values[1]
        return self.evaluate(node.get("left"), scope), self.evaluate(node.get("right"), scope)

    def ordered_comparison(
        self,
        node: dict[str, Any],
        scope: NativeScope,
        compare: Callable[[Any, Any], bool],
    ) -> bool:
        values = self.component_list(node, scope)
        try:
            return all(compare(left, right) for left, right in zip(values, values[1:]))
        except TypeError:
            return False

class NativeRuntime:
    """Execute event mechanics against authoritative native state."""

    def __init__(
        self,
        definition: dict[str, Any],
        state: dict[str, Any],
        *,
        random_source: random.Random | None = None,
        view_values: dict[str, Any] | None = None,
    ) -> None:
        self.definition = definition
        self.state = deepcopy(state)
        self.evaluator = NativeEvaluator(definition, self.state, random_source=random_source)
        self.execution = NativeExecution(state=self.state)
        self.event_queue: list[dict[str, Any]] = []
        self.current_event: dict[str, Any] = {}
        self.current_mechanic_token = ""
        self.current_effect_index = 0
        self.current_resource_definition = ""
        self.view_values = deepcopy(view_values or {})

    def fire(self, event_name: str, payload: dict[str, Any] | None = None) -> NativeExecution:
        """Process one event and every synchronously emitted follow-up event."""
        self.event_queue.append({"name": event_name, "payload": payload or {}})
        processed = 0
        while self.event_queue:
            if processed >= 1_000:
                raise NativeRuntimeError("Native event cascade exceeded 1,000 events.")
            event = self.event_queue.pop(0)
            self.execution.fired_events.append(deepcopy(event))
            self.current_event = event
            self.run_event(event)
            processed += 1
        return self.execution

    def remove_resource(
        self,
        resource_identifier: str,
        event_name: str = "rpg_onRemove",
    ) -> NativeExecution:
        """Revert opted-in mechanics before a resource leaves a character."""
        event = {"name": event_name, "payload": {"id": resource_identifier}}
        self.execution.fired_events.append(deepcopy(event))
        for resource, parent in native_resources(self.state):
            if native_resource_identifier(resource) != resource_identifier:
                continue
            resource_id = resource.get("resource_id")
            definition = self.resource_definition(resource_id)
            stats = resource.get("stats")
            if definition is None or not isinstance(stats, dict):
                break
            scope = NativeScope(
                values=stats,
                character=self.state,
                parent=parent,
                global_values={"event": event, "$event": event},
                view=self.view_values,
            )
            previous_evaluator = self.evaluator
            previous_resource_definition = self.current_resource_definition
            self.current_resource_definition = str(resource_id)
            self.evaluator = NativeEvaluator(
                definition,
                stats,
                random_source=previous_evaluator.random,
                character_evaluator=previous_evaluator,
            )
            try:
                owner = f"{resource.get('resource_id')}:{resource_identifier}"
                for mechanic in definition.get("mechanics", []):
                    if not isinstance(mechanic, dict):
                        continue
                    self.current_mechanic_token = (
                        f"{owner}:{mechanic.get('id', 'mechanic')}"
                    )
                    condition = mechanic.get("revert_on_remove")
                    if condition is not None and bool(
                        self.evaluator.evaluate(condition, scope)
                    ):
                        self.revert_mechanic(scope)
            finally:
                self.evaluator = previous_evaluator
                self.current_resource_definition = previous_resource_definition
            break
        return self.execution

    def run_event(self, event: dict[str, Any]) -> None:
        event_values = {**event, **event.get("payload", {})}
        scope = NativeScope(
            values=self.state,
            character=self.state,
            global_values={"event": event_values, "$event": event_values},
            view=self.view_values,
        )
        self.run_mechanics(
            self.definition.get("mechanics", []),
            scope,
            event,
            owner_token="system",
        )
        for resource, parent in native_resources(self.state):
            resource_id = resource.get("resource_id")
            definition = self.resource_definition(resource_id)
            if definition is None:
                continue
            stats = resource.get("stats")
            if not isinstance(stats, dict):
                continue
            resource_scope = NativeScope(
                values=stats,
                character=self.state,
                parent=parent,
                global_values={"event": event_values, "$event": event_values},
                view=self.view_values,
            )
            previous_evaluator = self.evaluator
            previous_resource_definition = self.current_resource_definition
            self.current_resource_definition = str(resource_id)
            self.evaluator = NativeEvaluator(
                definition,
                stats,
                random_source=previous_evaluator.random,
                resource_lookup=previous_evaluator.resource_lookup,
                character_evaluator=previous_evaluator,
            )
            try:
                identifier = native_resource_identifier(resource)
                owner_token = f"{resource_id}:{identifier}"
                self.run_mechanics(
                    definition.get("mechanics", []),
                    resource_scope,
                    event,
                    owner_token=owner_token,
                    resource_identifier=identifier,
                )
            finally:
                self.evaluator = previous_evaluator
                self.current_resource_definition = previous_resource_definition

    def run_mechanics(
        self,
        mechanics: Any,
        scope: NativeScope,
        event: dict[str, Any],
        *,
        owner_token: str,
        resource_identifier: str = "",
    ) -> None:
        """Execute and revert mechanics belonging to one character or resource."""
        for mechanic in mechanics if isinstance(mechanics, list) else []:
            if not isinstance(mechanic, dict):
                continue
            identifier = str(mechanic.get("id", "mechanic"))
            self.current_mechanic_token = f"{owner_token}:{identifier}"
            names = self.mechanic_event_names(
                mechanic,
                scope,
                resource_identifier=resource_identifier,
            )
            if event["name"] in names:
                self.current_effect_index = 0
                self.execute_effect(mechanic.get("effects"), scope)

            revert_names = self.mechanic_revert_event_names(
                mechanic,
                scope,
                resource_identifier=resource_identifier,
            )
            if event["name"] in revert_names:
                self.revert_mechanic(scope)

    def mechanic_event_names(
        self,
        mechanic: dict[str, Any],
        scope: NativeScope,
        *,
        resource_identifier: str = "",
    ) -> list[str]:
        names = event_name_list(mechanic.get("event_names", []))
        if resource_identifier:
            names = [decorate_event_name(name, resource_identifier) for name in names]
        calculated = mechanic.get("calculated_event_names")
        if calculated is not None:
            names.extend(event_name_list(self.evaluator.evaluate(calculated, scope)))
        return names

    def mechanic_revert_event_names(
        self,
        mechanic: dict[str, Any],
        scope: NativeScope,
        *,
        resource_identifier: str = "",
    ) -> list[str]:
        names = event_name_list(mechanic.get("revert_event_names", []))
        if resource_identifier:
            names = [decorate_event_name(name, resource_identifier) for name in names]
        calculated = mechanic.get("calculated_revert_event_names")
        if calculated is not None:
            names.extend(event_name_list(self.evaluator.evaluate(calculated, scope)))
        return names

    def resource_definition(self, identifier: Any) -> dict[str, Any] | None:
        for definition in self.definition.get("resources", []):
            if isinstance(definition, dict) and definition.get("id") == identifier:
                return definition
        return None

    def execute_effect(self, effect: Any, scope: NativeScope) -> None:
        """Execute one compiled effect node and record every externally visible action."""
        if effect is None:
            return
        if isinstance(effect, list):
            for child in effect:
                self.execute_effect(child, scope)
            return
        if not isinstance(effect, dict):
            raise NativeRuntimeError("Native effect must be an object.")
        effect_type = effect.get("type")
        handler = getattr(self, f"effect_{effect_type}", None)
        if handler is None:
            self.execution.unsupported.append(deepcopy(effect))
            raise NativeRuntimeError(f"Unsupported effect type: {effect_type}.")
        handler(effect, scope)

    def effect_sequence(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.execute_effect(effect.get("effects", []), scope)

    def effect_when(self, effect: dict[str, Any], scope: NativeScope) -> None:
        for clause in effect.get("clauses", []):
            if not isinstance(clause, dict):
                continue
            if bool(self.evaluator.evaluate(clause.get("condition"), scope)):
                self.execute_effect(clause.get("effect"), scope)
                return

    def effect_setStat(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.apply_stat_change(effect, scope, replace=True)

    def effect_addToStat(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.apply_stat_change(effect, scope, replace=False)

    def effect_fireEvent(self, effect: dict[str, Any], scope: NativeScope) -> None:
        event = effect.get("event")
        if isinstance(event, dict) and isinstance(event.get("name"), str):
            payload = self.evaluator.evaluate(event.get("payload", {}), scope)
            self.event_queue.append({"name": event["name"], "payload": payload or {}})
            return
        names = self.evaluator.evaluate(effect.get("event_names"), scope)
        if isinstance(names, str):
            names = [names]
        for name in names or []:
            self.event_queue.append({"name": str(name), "payload": {}})

    def effect_forwardEvent(self, effect: dict[str, Any], scope: NativeScope) -> None:
        names = self.evaluator.evaluate(effect.get("new_event_names"), scope)
        for name in names if isinstance(names, list) else [names]:
            if name:
                self.event_queue.append(
                    {
                        "name": str(name),
                        "payload": deepcopy(self.current_event.get("payload", {})),
                    }
                )

    def effect_forEach(self, effect: dict[str, Any], scope: NativeScope) -> None:
        values = self.evaluator.evaluate(effect.get("components"), scope) or []
        key = effect.get("for_each_value_key", "$forEachValue")
        for value in values:
            apply = effect.get("apply", effect.get("effect"))
            self.execute_effect(apply, scope.child(**{str(key): value}))

    def effect_roll(self, effect: dict[str, Any], scope: NativeScope) -> None:
        rollables = self.evaluator.evaluate(effect.get("rolls"), scope) or []
        results: list[dict[str, Any]] = []
        for rollable in rollables:
            if not isinstance(rollable, dict):
                continue
            formulas = self.evaluator.evaluate(rollable.get("formulas"), scope) or []
            formulas = formulas if isinstance(formulas, list) else [formulas]
            values = [
                roll_formula(str(formula), self.evaluator.random)
                for formula in formulas
            ]
            results.append(
                {
                    "text": self.evaluator.evaluate(rollable.get("text"), scope),
                    "formulas": formulas,
                    "results": values,
                    "total": sum(values),
                }
            )
        self.execution.interface_actions.append({"type": "roll", "rolls": results})
        on_result = effect.get("on_result_effect")
        if on_result is not None and results:
            event = {"result": results[0]["total"], "rolls": results}
            child = scope.child(**{"$event": event})
            self.execute_effect(on_result, child)

    def effect_delayed(self, effect: dict[str, Any], scope: NativeScope) -> None:
        due_at = datetime.now(UTC) + timedelta(milliseconds=int(effect.get("millis", 0)))
        self.execution.delayed_effects.append(
            {
                "id": str(uuid.uuid4()),
                "millis": int(effect.get("millis", 0)),
                "due_at": due_at.isoformat(),
                "effect": deepcopy(effect.get("effect")),
                "mechanic": self.current_mechanic_token,
                "resource_definition": self.current_resource_definition,
                "scope_path": find_native_object_path(self.state, scope.values),
                "parent_path": find_native_object_path(self.state, scope.parent),
                "event": deepcopy(self.current_event),
                "view_values": deepcopy(scope.view),
                "locals": deepcopy(scope.locals),
            }
        )

    def execute_delayed(self, delayed: dict[str, Any]) -> NativeExecution:
        """Execute a previously captured delayed child effect in its native scope."""
        delayed_id = str(delayed.get("id", ""))
        self.execution.fired_events.append(
            {"name": f"rpg_delayed:{delayed_id}", "payload": {}}
        )
        scope_path = delayed.get("scope_path")
        values = native_value_at_path(self.state, scope_path)
        if not isinstance(values, dict):
            values = self.state
        parent = native_value_at_path(self.state, delayed.get("parent_path"))
        event = delayed.get("event")
        event = event if isinstance(event, dict) else {}
        view = delayed.get("view_values")
        locals_values = delayed.get("locals")
        scope = NativeScope(
            values=values,
            character=self.state,
            parent=parent if isinstance(parent, dict) else None,
            global_values={"event": event, "$event": event},
            view=view if isinstance(view, dict) else {},
            locals=locals_values if isinstance(locals_values, dict) else {},
        )
        resource_definition = str(delayed.get("resource_definition", ""))
        if resource_definition:
            definition = self.resource_definition(resource_definition)
            if definition is None:
                raise NativeRuntimeError(
                    f"Delayed resource definition {resource_definition} is unavailable."
                )
            character_evaluator = self.evaluator
            self.evaluator = NativeEvaluator(
                definition,
                values,
                random_source=character_evaluator.random,
                character_evaluator=character_evaluator,
            )
        else:
            character_evaluator = None
        self.current_mechanic_token = str(delayed.get("mechanic", ""))
        self.current_resource_definition = resource_definition
        try:
            self.execute_effect(delayed.get("effect"), scope)
        finally:
            if character_evaluator is not None:
                self.evaluator = character_evaluator
        return self.execution

    def effect_showMessage(self, effect: dict[str, Any], scope: NativeScope) -> None:
        message = self.evaluator.evaluate(effect.get("message"), scope) if isinstance(effect.get("message"), dict) else effect.get("message")
        self.execution.messages.append(
            {"message": str(message or ""), "message_type": effect.get("message_type", "info")}
        )

    def effect_showPopUp(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.interface_effect(effect, scope)

    def effect_showResource(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.interface_effect(effect, scope)

    def effect_dismissResource(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.interface_effect(effect, scope)

    def effect_copyResource(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.interface_effect(effect, scope)

    def interface_effect(self, effect: dict[str, Any], scope: NativeScope) -> None:
        self.execution.interface_actions.append(
            {**deepcopy(effect), "resolved_components": self.evaluator.evaluate(effect.get("components"), scope)}
        )

    def apply_stat_change(self, effect: dict[str, Any], scope: NativeScope, *, replace: bool) -> None:
        identifier = effect.get("stat")
        if not isinstance(identifier, str):
            identifier = self.evaluator.evaluate(effect.get("meta_stat"), scope)
        if not isinstance(identifier, str) or not identifier:
            raise NativeRuntimeError("Native stat mutation has no valid target.")
        value_node = effect.get("new_value") if replace else effect.get("value")
        value = self.evaluator.evaluate(value_node, scope)
        concrete_path = concrete_native_path(identifier, scope, self.state)
        previous = deepcopy(self.evaluator.resolve_path(identifier, scope))
        runtime_state = self.state.setdefault("$hoard_runtime", {})
        overrides = runtime_state.setdefault("overrides", [])
        aggregation = effect.get("aggregation_type")
        if aggregation is None and effect.get("calculated_aggregation_type") is not None:
            aggregation = self.evaluator.evaluate(
                effect.get("calculated_aggregation_type"),
                scope,
            )
        aggregation = str(aggregation or "none")
        if aggregation not in {"max", "min", "none", "set", "sum"}:
            raise NativeRuntimeError(f"Unsupported aggregation type: {aggregation}.")
        if aggregation == "set":
            updated = (
                deepcopy(value)
                if replace
                else add_native_values(previous, value)
            )
            root_scope = NativeScope(
                values=self.state,
                character=self.state,
                global_values=scope.global_values,
                view=scope.view,
                locals=scope.locals,
            )
            set_native_path(concrete_path, updated, root_scope, self.state)
            runtime_state.setdefault("reversions", []).append(
                {
                    "mechanic": self.current_mechanic_token,
                    "path": concrete_path,
                    "before": previous,
                }
            )
            self.current_effect_index += 1
            self.evaluator.cache.clear()
            self.execution.changes.append(
                {
                    "stat": identifier,
                    "path": concrete_path,
                    "before": previous,
                    "after": deepcopy(updated),
                    "override_kind": "value" if replace else "modifier",
                    "aggregation": aggregation,
                }
            )
            return
        bases = runtime_state.setdefault("override_bases", {})
        if concrete_path not in bases:
            bases[concrete_path] = deepcopy(previous)
        effect_index = self.current_effect_index
        self.current_effect_index += 1
        kind = "value" if replace else "modifier"
        overrides[:] = [
            override
            for override in overrides
            if not (
                override.get("mechanic") == self.current_mechanic_token
                and override.get("effect_index") == effect_index
                and override.get("path") == concrete_path
                and override.get("kind") == kind
            )
        ]
        order = int(runtime_state.get("override_order", 0)) + 1
        runtime_state["override_order"] = order
        overrides.append(
            {
                "mechanic": self.current_mechanic_token,
                "effect_index": effect_index,
                "path": concrete_path,
                "kind": kind,
                "aggregation": aggregation,
                "value": deepcopy(value),
                "order": order,
            }
        )
        updated = self.apply_overrides(concrete_path, scope)
        self.evaluator.cache.clear()
        self.execution.changes.append(
            {
                "stat": identifier,
                "path": concrete_path,
                "before": previous,
                "after": deepcopy(updated),
                "override_kind": kind,
                "aggregation": aggregation,
            }
        )

    def apply_overrides(self, path: str, scope: NativeScope) -> Any:
        """Aggregate active value and modifier overrides for one concrete path."""
        runtime_state = self.state.setdefault("$hoard_runtime", {})
        reversions = runtime_state.setdefault("reversions", [])
        retained_reversions = []
        matching_reversions = []
        for change in reversions:
            if change.get("mechanic") == self.current_mechanic_token:
                matching_reversions.append(change)
            else:
                retained_reversions.append(change)
        for change in reversed(matching_reversions):
            path = change.get("path")
            if not isinstance(path, str):
                continue
            root_scope = NativeScope(values=self.state, character=self.state)
            previous = deepcopy(self.evaluator.resolve_path(path, root_scope))
            restored = deepcopy(change.get("before"))
            set_native_path(path, restored, root_scope, self.state)
            self.execution.changes.append(
                {
                    "stat": path,
                    "path": path,
                    "before": previous,
                    "after": restored,
                    "reverted": True,
                }
            )
        runtime_state["reversions"] = retained_reversions
        overrides = runtime_state.setdefault("overrides", [])
        base = deepcopy(runtime_state.setdefault("override_bases", {}).get(path))
        value_overrides = [
            value
            for value in overrides
            if value.get("path") == path and value.get("kind") == "value"
        ]
        modifier_overrides = [
            value
            for value in overrides
            if value.get("path") == path and value.get("kind") == "modifier"
        ]
        overridden = self.aggregate_overrides(path, "value", value_overrides)
        modified = self.aggregate_overrides(path, "modifier", modifier_overrides)
        result = overridden if value_overrides else base
        if modifier_overrides:
            result = add_native_values(result, modified)
        root_scope = NativeScope(
            values=self.state,
            character=self.state,
            global_values=scope.global_values,
            view=scope.view,
            locals=scope.locals,
        )
        set_native_path(path, result, root_scope, self.state)
        return result

    def aggregate_overrides(
        self,
        path: str,
        kind: str,
        overrides: list[dict[str, Any]],
    ) -> Any:
        """Apply native max/min/sum/set rules and expose prompt conflicts."""
        if not overrides:
            return None
        overrides.sort(key=lambda value: int(value.get("order", 0)))
        aggregations = {str(value.get("aggregation", "none")) for value in overrides}
        if len(overrides) > 1 and (
            "none" in aggregations or len(aggregations) > 1
        ):
            self.execution.interface_actions.append(
                {
                    "type": "resolveOverride",
                    "stat": path,
                    "override_kind": kind,
                    "aggregations": sorted(aggregations),
                    "choices": deepcopy(overrides),
                }
            )
            return deepcopy(overrides[-1].get("value"))
        aggregation = str(overrides[-1].get("aggregation", "none"))
        values = [deepcopy(value.get("value")) for value in overrides]
        if len(values) == 1 or aggregation in {"none", "set"}:
            return values[-1]
        if aggregation == "sum":
            result = neutral_native_value(values[0])
            for value in values:
                result = add_native_values(result, value)
            return result
        try:
            return min(values) if aggregation == "min" else max(values)
        except TypeError as error:
            raise NativeRuntimeError(
                f"Cannot apply {aggregation} aggregation to {path}."
            ) from error

    def revert_mechanic(self, scope: NativeScope) -> None:
        """Undo reversible stat effects previously applied by the current mechanic."""
        runtime_state = self.state.setdefault("$hoard_runtime", {})
        overrides = runtime_state.setdefault("overrides", [])
        matching = [
            value
            for value in overrides
            if value.get("mechanic") == self.current_mechanic_token
        ]
        runtime_state["overrides"] = [
            value
            for value in overrides
            if value.get("mechanic") != self.current_mechanic_token
        ]
        for path in dict.fromkeys(
            str(value.get("path")) for value in matching if value.get("path")
        ):
            root_scope = NativeScope(values=self.state, character=self.state)
            previous = deepcopy(self.evaluator.resolve_path(path, root_scope))
            restored = self.apply_overrides(path, scope)
            self.execution.changes.append(
                {
                    "stat": path,
                    "path": path,
                    "before": previous,
                    "after": restored,
                    "reverted": True,
                }
            )
        self.evaluator.cache.clear()


def unwrap_native_value(value: Any) -> Any:
    """Unwrap the storage wrapper used by native resource-instance stats."""
    if isinstance(value, dict) and set(value).issuperset({"value"}):
        return value.get("value")
    return value


def flatten(values: Any) -> list[Any]:
    """Flatten arrays by one recursive sequence level as native flatAppend does."""
    result: list[Any] = []
    for value in values if isinstance(values, list) else [values]:
        if isinstance(value, list):
            result.extend(flatten(value))
        else:
            result.append(value)
    return result


def unique_values(values: list[Any]) -> list[Any]:
    """Retain first-seen values when native composition requests set semantics."""
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def sortable_value(value: Any) -> tuple[bool, Any]:
    """Sort nulls consistently after concrete values."""
    return value is None, value


def native_resource_identifier(value: Any) -> str:
    """Read an ID from a native resource value or stat wrapper."""
    value = unwrap_native_value(value)
    if not isinstance(value, dict):
        return ""
    identifier = value.get("id")
    if not isinstance(identifier, str):
        stats = value.get("stats")
        identifier = unwrap_native_value(stats.get("id")) if isinstance(stats, dict) else None
    return identifier if isinstance(identifier, str) else ""


def native_path_parts(path: str) -> list[str]:
    """Split the contract's optional dotted path notation."""
    return [part.rstrip("?") for part in path.replace("?.", ".").split(".")]


def concrete_native_path(
    path: str,
    scope: NativeScope,
    root_state: dict[str, Any],
) -> str:
    """Resolve a scoped mutation target to a stable path in character state."""
    parts = native_path_parts(path)
    first = parts.pop(0)
    if first == "$character":
        return ".".join(parts)
    if first.startswith("$"):
        target = scope.locals.get(first)
        prefix = find_native_object_path(root_state, target)
        if prefix is None:
            raise NativeRuntimeError(f"Native mutation target {first} is unavailable.")
        return ".".join([*prefix, *parts])
    prefix = find_native_object_path(root_state, scope.values)
    return ".".join([*(prefix or []), first, *parts])


def find_native_object_path(root: Any, target: Any) -> list[str] | None:
    """Find an object already contained in native state by identity."""
    if root is target:
        return []
    if isinstance(root, dict):
        for key, value in root.items():
            if key == "$hoard_runtime":
                continue
            found = find_native_object_path(value, target)
            if found is not None:
                return [str(key), *found]
    elif isinstance(root, list):
        for index, value in enumerate(root):
            found = find_native_object_path(value, target)
            if found is not None:
                return [str(index), *found]
    return None


def native_value_at_path(root: Any, path: Any) -> Any:
    """Read a concrete dictionary/list path captured for delayed execution."""
    if not isinstance(path, list):
        return None
    current = root
    for part in path:
        if isinstance(current, dict):
            current = current.get(str(part))
        elif isinstance(current, list) and str(part).isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def neutral_native_value(value: Any) -> Any:
    """Return the additive identity matching a native override value."""
    if isinstance(value, list):
        return []
    if isinstance(value, str):
        return ""
    return 0


def add_native_values(left: Any, right: Any) -> Any:
    """Apply native modifier addition across numeric and collection stats."""
    if isinstance(left, list):
        return [*left, *(right if isinstance(right, list) else [right])]
    if isinstance(left, str):
        return left + str(right or "")
    return (left or 0) + (right or 0)


def set_native_path(
    path: str,
    value: Any,
    scope: NativeScope,
    root_state: dict[str, Any],
) -> None:
    """Set a root or lambda-scoped native stat while preserving wrappers."""
    parts = native_path_parts(path)
    first = parts.pop(0)
    if first == "$character":
        current = root_state
    elif first.startswith("$"):
        current = scope.locals.get(first)
        if current is None:
            raise NativeRuntimeError(f"Native mutation target {first} is unavailable.")
    else:
        if not parts:
            assign_native_value(scope.values, first, value)
            return
        current = scope.values.get(first)

    for part in parts[:-1]:
        if (
            isinstance(current, dict)
            and part in {"stats", "value"}
            and part in current
        ):
            current = current[part]
            continue
        current = unwrap_native_value(current)
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                raise NativeRuntimeError(f"Native mutation path {path} is invalid.")
            current = current[index]
            continue
        if not isinstance(current, dict):
            raise NativeRuntimeError(f"Native mutation path {path} is invalid.")
        stats = current.get("stats")
        if isinstance(stats, dict) and part in stats:
            current = stats[part]
        else:
            current = current.get(part)
    if not parts:
        raise NativeRuntimeError(f"Native mutation path {path} is invalid.")
    current = unwrap_native_container(current)
    if not isinstance(current, dict):
        raise NativeRuntimeError(f"Native mutation path {path} is invalid.")
    assign_native_value(current, parts[-1], value)


def unwrap_native_container(value: Any) -> Any:
    """Unwrap a native value wrapper only when it contains a nested container."""
    if isinstance(value, dict) and "value" in value:
        nested = value.get("value")
        if isinstance(nested, (dict, list)):
            return nested
    return value


def assign_native_value(container: dict[str, Any], key: str, value: Any) -> None:
    """Assign a value without discarding an existing native stat wrapper."""
    stats = container.get("stats")
    target = stats if isinstance(stats, dict) and key in stats else container
    existing = target.get(key)
    if isinstance(existing, dict) and "value" in existing:
        existing["value"] = deepcopy(value)
    else:
        target[key] = deepcopy(value)


def replace_resource_identifier(resource: Any) -> None:
    """Give a copied native resource a distinct stable instance identifier."""
    if not isinstance(resource, dict):
        return
    identifier = str(uuid.uuid4())
    stats = resource.get("stats")
    if isinstance(stats, dict) and "id" in stats:
        assign_native_value(stats, "id", identifier)
    elif "id" in resource:
        resource["id"] = identifier


def roll_formula(formula: str, random_source: random.Random) -> int:
    """Evaluate the integer and dice subset emitted by supported systems."""
    compact = re.sub(r"\s+", "", formula.lower())
    if not compact:
        return 0
    total = 0
    position = 0
    pattern = re.compile(r"([+-]?)(?:(max|min)\((\d+)d(\d+)\)|(\d*)d(\d+)|(\d+))")
    for match in pattern.finditer(compact):
        if match.start() != position:
            raise NativeRuntimeError(f"Unsupported dice formula: {formula}.")
        sign = -1 if match.group(1) == "-" else 1
        if match.group(2):
            rolls = [
                random_source.randint(1, int(match.group(4)))
                for unused in range(int(match.group(3)))
            ]
            result = max(rolls) if match.group(2) == "max" else min(rolls)
        elif match.group(6):
            amount = int(match.group(5) or 1)
            result = sum(
                random_source.randint(1, int(match.group(6)))
                for unused in range(amount)
            )
        else:
            result = int(match.group(7))
        total += sign * result
        position = match.end()
    if position != len(compact):
        raise NativeRuntimeError(f"Unsupported dice formula: {formula}.")
    return total


def event_name_list(value: Any) -> list[str]:
    """Normalize comma-separated and array subscriber event names."""
    if isinstance(value, str):
        return [name.strip() for name in value.split(",") if name.strip()]
    if isinstance(value, list):
        return [str(name) for name in value if str(name)]
    return []


def native_contract_report(definition: dict[str, Any]) -> dict[str, list[str]]:
    """Report native node types used by a compiled definition and unsupported ones."""
    formula_types = {
        name.removeprefix("evaluate_")
        for name in NativeEvaluator.__dict__
        if name.startswith("evaluate_")
    }
    effect_types = {
        name.removeprefix("effect_")
        for name in NativeRuntime.__dict__
        if name.startswith("effect_")
    }
    supported = formula_types | effect_types | SUPPORTED_NATIVE_VIEW_TYPES | {
        "base",
        "calculated",
    }
    used: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            node_type = value.get("type")
            if isinstance(node_type, str):
                used.add(node_type)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(definition)
    return {
        "used": sorted(used),
        "supported": sorted(used & supported),
        "unsupported": sorted(used - supported),
    }


def decorate_event_name(event_name: str, resource_identifier: str) -> str:
    """Scope a resource event consistently across subscribers and formulas."""
    return f"{event_name}:{resource_identifier}" if resource_identifier else event_name


def native_resources(
    value: Any,
    parent: dict[str, Any] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Discover every nested native resource instance in character state."""
    found: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    value = unwrap_native_value(value)
    if isinstance(value, dict):
        next_parent = parent
        if isinstance(value.get("resource_id"), str) and isinstance(
            value.get("stats"), dict
        ):
            found.append((value, parent))
            next_parent = value
        for key, child in value.items():
            if key == "$hoard_runtime":
                continue
            found.extend(native_resources(child, next_parent))
    elif isinstance(value, list):
        for child in value:
            found.extend(native_resources(child, parent))
    return found

from __future__ import annotations

import gzip
import io
import json
import random
from pathlib import Path
from tarfile import TarInfo
from tarfile import open as open_tarfile
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, TestCase

from hoard.compendium.ingest.repository import (
    SUPPORTED_SOURCE_IDENTIFIERS,
    _read_published_resources,
    _read_rpg_json,
    _supported_source_identifiers,
)
from hoard.compendium.ingest.sources import import_source_directory as import_rpg
from hoard.compendium.models import (
    CompendiumEntry,
    CompendiumRepository,
    CompendiumSource,
)
from hoard.compendium.native.packages import (
    compose_development_system,
    merge_native_values,
    read_published_system,
)
from hoard.compendium.native.runtime import (
    SUPPORTED_NATIVE_VIEW_TYPES,
    NativeEvaluator,
    NativeRuntime,
    NativeRuntimeError,
    NativeScope,
    native_contract_report,
    roll_formula,
)


class PublishedPackageTests(SimpleTestCase):
    def test_only_5e_sources_are_supported(self):
        self.assertEqual(SUPPORTED_SOURCE_IDENTIFIERS, {"5e", "5e2024"})
        self.assertEqual(_supported_source_identifiers({"5e", "pf2e"}), {"5e"})
        self.assertEqual(_supported_source_identifiers({"pf2e"}), set())

    def test_reads_rpg_companion_published_package(self):
        resource = {
            "resource_id": "background",
            "stats": {"id": {"value": "obojima-background"}},
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "systems.rpg").write_bytes(
                gzip.compress(json.dumps({"systems": [{"id": "5e"}]}).encode())
            )
            bundle = io.BytesIO()
            with open_tarfile(fileobj=bundle, mode="w") as archive:
                encoded_resource = gzip.compress(json.dumps(resource).encode())
                member = TarInfo("background/obojima-background.rpg")
                member.size = len(encoded_resource)
                archive.addfile(member, io.BytesIO(encoded_resource))
            (root / "resources.rpg.gzip").write_bytes(gzip.compress(bundle.getvalue()))

            self.assertEqual(
                _read_rpg_json(root / "systems.rpg"), {"systems": [{"id": "5e"}]}
            )
            self.assertEqual(
                _read_published_resources(root / "resources.rpg.gzip"),
                [(resource, "obojima-background")],
            )

    def test_reads_a_compiled_system_definition(self):
        definition = {"id": "5e", "version": "1.0", "character_stats": []}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "system.rpg"
            path.write_bytes(gzip.compress(json.dumps(definition).encode()))

            self.assertEqual(read_published_system(path), definition)

    def test_5e_long_rest_restores_slots_from_a_calculated_class_resource(self):
        repository_root = Path(__file__).resolve().parents[3]
        system = read_published_system(
            repository_root / "hoard/compendium/systems/compiled/5e/system.rpg"
        )
        wizard = json.loads(
            (
                repository_root
                / "hoard/compendium/systems/default/systems/5e/resource_instances"
                / "class_wizard_wizard.rpg.json"
            ).read_text()
        )
        state = NativeEvaluator(system, {}).default_state()
        state["classes"] = [
            {
                "resource_id": "class_details",
                "stats": {
                    "id": {"value": "class-details:wizard"},
                    "class": {"value": wizard},
                    "class_level": {"value": 3},
                    "archetype_id": {"value": None},
                    "selected_selectable_feature_ids": {"value": []},
                    "last_selection_level": {"value": 0},
                },
            }
        ]
        state["intelligence_score"] = 16
        state["level"] = 3

        execution = NativeRuntime(system, state).fire("long_rest")

        self.assertEqual(execution.state["spell_slots_1"], 4)
        self.assertEqual(execution.state["spell_slots_2"], 2)

        class_details = next(
            resource
            for resource in system["resources"]
            if resource["id"] == "class_details"
        )
        character_evaluator = NativeEvaluator(system, state)
        details = state["classes"][0]["stats"]
        class_evaluator = NativeEvaluator(
            class_details,
            details,
            character_evaluator=character_evaluator,
        )
        scope = NativeScope(values=details, character=state, parent=state)

        self.assertTrue(class_evaluator.stat("show_spellcasting_details", scope))
        self.assertEqual(
            class_evaluator.stat("class.actual_spellcasting_ability", scope),
            "intelligence",
        )
        self.assertEqual(class_evaluator.stat("spell_attack_bonus", scope), 5)
        self.assertEqual(class_evaluator.stat("spell_save_dc", scope), 13)


class NativeCompositionTests(SimpleTestCase):
    def test_deep_merge_merges_identified_stats_without_reordering(self):
        base = {
            "stats": [
                {"id": "name", "default_value": ""},
                {"id": "level", "default_value": 1},
            ],
            "tags": ["base"],
        }
        overlay = {
            "stats": [
                {"id": "level", "name": "Level"},
                {"id": "xp", "default_value": 0},
            ],
            "tags": ["overlay"],
        }

        merged = merge_native_values(base, overlay)

        self.assertEqual([stat["id"] for stat in merged["stats"]], ["name", "level", "xp"])
        self.assertEqual(merged["stats"][1], {"id": "level", "default_value": 1, "name": "Level"})
        self.assertEqual(merged["tags"], ["base", "overlay"])

    def test_composes_json_development_layout_and_marks_rpgscript_status(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / "system"
            resource = system / "resources" / "spell"
            resource.mkdir(parents=True)
            (system / "system.rpg.json").write_text(
                json.dumps({"id": "5e", "name": "Five"}), encoding="utf-8"
            )
            (resource / "index.rpg.json").write_text(
                json.dumps({"id": "spell", "name": "Spell"}), encoding="utf-8"
            )
            (resource / "stats.rpg.json").write_text(
                json.dumps([{"id": "name", "type": "base"}]), encoding="utf-8"
            )

            definition = compose_development_system(root)

        self.assertEqual(definition["resources"][0]["id"], "spell")
        self.assertEqual(definition["resources"][0]["stats"][0]["id"], "name")
        self.assertTrue(definition["hoard_composition"]["rpgscript_compiled"])


class NativeRuntimeTests(SimpleTestCase):
    definition = {
        "character_stats": [
            {"id": "base_hp", "type": "base", "default_value": 4},
            {
                "id": "max_hp",
                "type": "calculated",
                "components": {
                    "type": "add",
                    "components": {
                        "type": "list",
                        "components": [
                            {"type": "stat", "stat": "base_hp"},
                            {"type": "constant", "value": 3},
                        ],
                    },
                },
            },
        ],
        "mechanics": [
            {
                "id": "rest",
                "event_names": "long_rest",
                "effects": {
                    "type": "sequence",
                    "effects": [
                        {
                            "type": "setStat",
                            "stat": "current_hp",
                            "new_value": {"type": "stat", "stat": "max_hp"},
                            "aggregation_type": "set",
                        },
                        {
                            "type": "showMessage",
                            "message": "Restored",
                            "message_type": "info",
                        },
                    ],
                },
            }
        ],
    }

    def test_evaluates_calculated_stats_and_native_events(self):
        state = {"base_hp": 9, "current_hp": 1}
        evaluator = NativeEvaluator(self.definition, state)
        scope = NativeScope(values=state, character=state)

        self.assertEqual(evaluator.stat("max_hp", scope), 12)

        execution = NativeRuntime(self.definition, state).fire("long_rest")

        self.assertEqual(execution.state["current_hp"], 12)
        self.assertEqual(execution.changes[0]["before"], 1)
        self.assertEqual(execution.messages[0]["message"], "Restored")

    def test_unsupported_nodes_are_never_silently_ignored(self):
        evaluator = NativeEvaluator(self.definition, {})

        with self.assertRaisesMessage(NativeRuntimeError, "Unsupported calculation"):
            evaluator.evaluate({"type": "futureNode"})

    def test_resolves_calculated_stats_on_nested_resources(self):
        definition = {
            "character_stats": [
                {
                    "id": "class_details",
                    "type": "base",
                    "default_value": {},
                }
            ],
            "resources": [
                {
                    "id": "class",
                    "stats": [
                        {
                            "id": "effective_caster_level",
                            "type": "base",
                            "default_value": "zero",
                        },
                        {
                            "id": "is_spellcaster",
                            "type": "calculated",
                            "components": {
                                "type": "notEquals",
                                "components": {
                                    "type": "list",
                                    "components": [
                                        {
                                            "type": "stat",
                                            "stat": "effective_caster_level",
                                        },
                                        {"type": "constant", "value": "zero"},
                                    ],
                                },
                            },
                        },
                    ],
                }
            ],
        }
        state = {
            "class_details": {
                "resource_id": "class",
                "stats": {
                    "effective_caster_level": {"value": "full"},
                },
            }
        }
        evaluator = NativeEvaluator(definition, state)
        scope = NativeScope(values=state, character=state)

        self.assertTrue(evaluator.stat("class_details.is_spellcaster", scope))

    def test_compiled_lambda_names_optional_paths_and_append(self):
        state = {
            "classes": [
                {"stats": {"class_level": {"value": 2}}},
                {"stats": {"class_level": {"value": 4}}},
            ]
        }
        evaluator = NativeEvaluator({}, state)
        scope = NativeScope(values=state, character=state, view={"choice": "wizard"})
        levels = evaluator.evaluate(
            {
                "type": "map",
                "components": {"type": "stat", "stat": "classes"},
                "map_value_key": "$class",
                "mapper": {"type": "stat", "stat": "$class.class_level"},
            },
            scope,
        )
        appended = evaluator.evaluate(
            {
                "type": "append",
                "list": {"type": "constant", "value": ["a"]},
                "item": {"type": "stat", "stat": "$view?.choice?"},
            },
            scope,
        )

        self.assertEqual(levels, [2, 4])
        self.assertEqual(appended, ["a", "wizard"])

    def test_contract_enumerations_resource_stats_and_custom_lambda_keys(self):
        definition = {
            "enumerated_types": [
                {
                    "id": "schools",
                    "types": [
                        {"id": "abjuration", "name": "Abjuration", "abbreviation": "Abj."}
                    ],
                }
            ],
            "resources": [
                {
                    "id": "counter",
                    "stats": [
                        {"id": "value", "type": "base", "default_value": 0},
                        {
                            "id": "doubled",
                            "type": "calculated",
                            "components": {
                                "type": "multiply",
                                "components": {
                                    "type": "list",
                                    "components": [
                                        {"type": "stat", "stat": "value"},
                                        {"type": "constant", "value": 2},
                                    ],
                                },
                            },
                        },
                    ],
                }
            ],
        }
        resource = {
            "resource_id": "counter",
            "stats": {"value": {"value": 4}},
        }
        evaluator = NativeEvaluator(definition, {})
        scope = NativeScope(values={}, character={})

        self.assertEqual(
            evaluator.evaluate(
                {
                    "type": "enumeratedAbbreviation",
                    "enumerated_type": "schools",
                    "id": "abjuration",
                },
                scope,
            ),
            "Abj.",
        )
        self.assertEqual(
            evaluator.evaluate(
                {
                    "type": "stat",
                    "stat": "doubled",
                    "for_resource": {"type": "constant", "value": resource},
                },
                scope,
            ),
            8,
        )
        self.assertEqual(
            evaluator.evaluate(
                {
                    "type": "sortBy",
                    "components": {"type": "constant", "value": [3, 1, 2]},
                    "sort_by_value_key": "$number",
                    "sort_by_selector": {"type": "stat", "stat": "$number"},
                },
                scope,
            ),
            [1, 2, 3],
        )
        self.assertEqual(
            evaluator.evaluate(
                {
                    "type": "append",
                    "list": {"type": "constant", "value": ["a"]},
                    "item": {"type": "constant", "value": "a"},
                    "treat_as_set": True,
                },
                scope,
            ),
            ["a"],
        )

    def test_for_each_can_mutate_nested_wrapped_resource_stats(self):
        definition = {
            "mechanics": [
                {
                    "event_names": "advance",
                    "effects": {
                        "type": "forEach",
                        "components": {"type": "stat", "stat": "classes"},
                        "for_each_value_key": "$class",
                        "apply": {
                            "type": "addToStat",
                            "stat": "$class.class_level",
                            "value": {"type": "constant", "value": 1},
                        },
                    },
                }
            ]
        }
        state = {"classes": [{"stats": {"class_level": {"value": 2}}}]}

        execution = NativeRuntime(definition, state).fire("advance")

        self.assertEqual(
            execution.state["classes"][0]["stats"]["class_level"]["value"],
            3,
        )

    def test_formula_roll_supports_advantage_and_modifiers(self):
        seeded = random.Random(4)

        self.assertEqual(roll_formula("max(2d20) + 3", seeded), 13)

    def test_runtime_implements_every_tool_schema_formula_and_effect(self):
        schema_path = (
            Path(__file__).parents[1]
            / "native"
            / "tools"
            / "linux-x64"
            / "assets"
            / "dev_tool_schema.json"
        )
        classes = json.loads(schema_path.read_text(encoding="utf-8"))["classes"]
        formula_types = {
            definition["id"]
            for definition in classes.values()
            if definition.get("parent") == "StatFormulaComponent"
            and isinstance(definition.get("id"), str)
        }
        effect_types = {
            definition["id"]
            for definition in classes.values()
            if definition.get("parent") == "Effect"
            and isinstance(definition.get("id"), str)
        }

        missing_formulas = {
            node_type
            for node_type in formula_types
            if not hasattr(NativeEvaluator, f"evaluate_{node_type}")
        }
        missing_effects = {
            node_type
            for node_type in effect_types
            if not hasattr(NativeRuntime, f"effect_{node_type}")
        }

        self.assertEqual(missing_formulas, set())
        self.assertEqual(missing_effects, set())
        view_types = {
            definition["id"]
            for definition in classes.values()
            if definition.get("parent") == "RPGView"
            and isinstance(definition.get("id"), str)
        }
        self.assertEqual(view_types - SUPPORTED_NATIVE_VIEW_TYPES, set())

    def test_contract_report_flags_only_unknown_nodes(self):
        report = native_contract_report(
            {
                "character_stats": [{"id": "name", "type": "base"}],
                "character_sheet_sections": [
                    {"id": "title", "view": {"id": "title", "type": "text"}}
                ],
                "mechanics": [{"effects": {"type": "futureEffect"}}],
            }
        )

        self.assertEqual(report["unsupported"], ["futureEffect"])

    def test_resource_mechanics_are_scoped_and_reversible(self):
        definition = {
            "resources": [
                {
                    "id": "effect",
                    "stats": [
                        {
                            "id": "id",
                            "type": "base",
                            "default_value": "",
                        },
                        {
                            "id": "bonus",
                            "type": "base",
                            "default_value": 0,
                        },
                    ],
                    "mechanics": [
                        {
                            "id": "toggle",
                            "event_names": "use",
                            "revert_event_names": "revert",
                            "effects": {
                                "type": "addToStat",
                                "stat": "$character.base_hp",
                                "value": {"type": "stat", "stat": "bonus"},
                            },
                        }
                    ],
                }
            ]
        }
        state = {
            "base_hp": 8,
            "effects": [
                {
                    "resource_id": "effect",
                    "stats": {
                        "id": {"value": "blessing"},
                        "bonus": {"value": 2},
                    },
                }
            ],
        }
        runtime = NativeRuntime(definition, state)

        applied = runtime.fire("use:blessing")
        self.assertEqual(applied.state["base_hp"], 10)

        reverted = runtime.fire("revert:blessing")
        self.assertEqual(reverted.state["base_hp"], 8)
        self.assertTrue(reverted.changes[-1]["reverted"])

    def test_nested_resource_mechanic_mutates_a_wrapped_stat(self):
        definition = {
            "resources": [
                {"id": "race", "stats": [], "mechanics": []},
                {"id": "trait", "stats": [], "mechanics": []},
                {
                    "id": "effect",
                    "stats": [
                        {
                            "id": "current_charges",
                            "type": "base",
                            "default_value": 0,
                        }
                    ],
                    "mechanics": [
                        {
                            "id": "recharge",
                            "calculated_event_names": {
                                "type": "constant",
                                "value": "long_rest",
                            },
                            "effects": {
                                "type": "setStat",
                                "stat": "current_charges",
                                "new_value": {"type": "constant", "value": 3},
                                "aggregation_type": "set",
                            },
                        }
                    ],
                },
            ]
        }
        state = {
            "race": [
                {
                    "resource_id": "race",
                    "stats": {
                        "traits": {
                            "value": [
                                {
                                    "resource_id": "trait",
                                    "stats": {
                                        "effects": {
                                            "value": [
                                                {
                                                    "resource_id": "effect",
                                                    "stats": {
                                                        "id": {"value": "recharge"},
                                                        "current_charges": {"value": 0},
                                                    },
                                                }
                                            ]
                                        }
                                    },
                                }
                            ]
                        }
                    },
                }
            ]
        }

        execution = NativeRuntime(definition, state).fire("long_rest")

        effect = execution.state["race"][0]["stats"]["traits"]["value"][0][
            "stats"
        ]["effects"]["value"][0]
        self.assertEqual(effect["stats"]["current_charges"]["value"], 3)
        self.assertEqual(
            execution.changes[0]["path"],
            "race.0.stats.traits.value.0.stats.effects.value.0.stats.current_charges",
        )

    def test_value_and_modifier_overrides_aggregate_and_revert_independently(self):
        definition = {
            "mechanics": [
                {
                    "id": "set-score",
                    "event_names": "set-score",
                    "revert_event_names": "unset-score",
                    "effects": {
                        "type": "setStat",
                        "stat": "score",
                        "new_value": {"type": "constant", "value": 20},
                        "aggregation_type": "max",
                    },
                },
                {
                    "id": "add-score",
                    "event_names": "add-score",
                    "revert_event_names": "unadd-score",
                    "effects": {
                        "type": "addToStat",
                        "stat": "score",
                        "value": {"type": "constant", "value": 2},
                        "aggregation_type": "sum",
                    },
                },
            ]
        }
        runtime = NativeRuntime(definition, {"score": 10})

        runtime.fire("add-score")
        self.assertEqual(runtime.state["score"], 12)
        runtime.fire("set-score")
        self.assertEqual(runtime.state["score"], 22)
        runtime.fire("unset-score")
        self.assertEqual(runtime.state["score"], 12)
        runtime.fire("unadd-score")
        self.assertEqual(runtime.state["score"], 10)

    def test_conflicting_override_aggregations_request_explicit_resolution(self):
        definition = {
            "mechanics": [
                {
                    "id": "first",
                    "event_names": "first",
                    "effects": {
                        "type": "setStat",
                        "stat": "score",
                        "new_value": {"type": "constant", "value": 15},
                        "aggregation_type": "max",
                    },
                },
                {
                    "id": "second",
                    "event_names": "second",
                    "effects": {
                        "type": "setStat",
                        "stat": "score",
                        "new_value": {"type": "constant", "value": 18},
                        "aggregation_type": "min",
                    },
                },
            ]
        }
        runtime = NativeRuntime(definition, {"score": 10})

        runtime.fire("first")
        execution = runtime.fire("second")

        resolution = execution.interface_actions[-1]
        self.assertEqual(resolution["type"], "resolveOverride")
        self.assertEqual(resolution["stat"], "score")
        self.assertEqual(resolution["aggregations"], ["max", "min"])

    def test_delayed_effect_captures_and_restores_its_execution_scope(self):
        definition = {
            "mechanics": [
                {
                    "id": "later",
                    "event_names": "schedule",
                    "effects": {
                        "type": "delayed",
                        "millis": 0,
                        "effect": {
                            "type": "addToStat",
                            "stat": "score",
                            "value": {"type": "constant", "value": 3},
                            "aggregation_type": "set",
                        },
                    },
                }
            ]
        }
        runtime = NativeRuntime(definition, {"score": 4})

        scheduled = runtime.fire("schedule").delayed_effects[0]
        execution = runtime.execute_delayed(scheduled)

        self.assertTrue(scheduled["id"])
        self.assertEqual(execution.state["score"], 7)
        self.assertEqual(execution.fired_events[-1]["name"], f"rpg_delayed:{scheduled['id']}")


class CompendiumIngestTests(TestCase):
    def _write_rpg_resource(
        self, root: Path, system: str, kind: str, identifier: str, name: str
    ) -> dict[str, object]:
        payload = {
            "resource_id": kind,
            "stats": {
                "id": {"value": identifier},
                "name": {"value": name},
                "source": {"value": "PHB"},
                "description": {"value": "Reference description"},
                "type": {"value": "sword"},
                "cost": {
                    "value": {
                        "stats": {
                            "value": {"value": 12},
                            "unit": {"value": "gold"},
                        }
                    }
                },
                "weight": {
                    "value": {
                        "stats": {
                            "value": {"value": 3},
                            "unit": {"value": "lb"},
                        }
                    }
                },
                "rarity": {"value": "common"},
                "is_magic": {"value": False},
                "requires_attunement": {"value": False},
            },
        }
        path = (
            root / "systems" / system / "resource_instances" / f"{identifier}.rpg.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def test_rpg_import_creates_distinct_sources_and_normalises_equipment(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = self._write_rpg_resource(root, "5e", "weapon", "sword", "Sword")
            self._write_rpg_resource(root, "5e2024", "weapon", "sword", "Sword")

            repository, _ = CompendiumRepository.objects.get_or_create(
                identifier="default",
                defaults={"name": "Default"},
            )
            source_2014 = CompendiumSource.objects.create(
                repository=repository, identifier="5e", name="5e"
            )
            source_2024 = CompendiumSource.objects.create(
                repository=repository, identifier="5e2024", name="5e2024"
            )
            self.assertEqual(
                import_rpg(root / "systems" / "5e", source_2014), (1, 0, 0)
            )
            self.assertEqual(
                import_rpg(root / "systems" / "5e2024", source_2024), (1, 0, 0)
            )

        sources = {
            source.identifier: source for source in CompendiumSource.objects.all()
        }
        entries = CompendiumEntry.objects.filter(name="Sword")
        self.assertEqual(entries.count(), 2)
        entry = entries.get(source=sources["5e"])
        self.assertEqual(entry.cost_amount, 12)
        self.assertEqual(entry.cost_currency, "gp")
        self.assertEqual(entry.weight_amount, 3)
        self.assertEqual(entry.weight_unit, "lb")
        self.assertEqual(entry.item_type, "sword")
        self.assertEqual(entry.data, payload)

"""Audit the fixed OR-LIB 50_0_1_w input and verify its lossless CSV views."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import platform
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE_ID = "orlib_50_0_1_w"
CASE = ROOT / "cases" / CASE_ID
SCHEMA = ROOT / "schema" / f"{CASE_ID}.schema.json"
GEN_FIELDS = {
    "bus_id": "Bus",
    "initial_status_h": "Initial status (h)",
    "initial_power_mw": "Initial power (MW)",
    "minimum_uptime_h": "Minimum uptime (h)",
    "minimum_downtime_h": "Minimum downtime (h)",
    "ramp_up_limit_mw": "Ramp up limit (MW)",
    "ramp_down_limit_mw": "Ramp down limit (MW)",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError(f"duplicate JSON key: {key}")
        fields[key] = value
    return fields


def reject_constant(token):
    raise ValueError(f"non-finite JSON token: {token}")


def csv_bytes(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def verify_or_create(path, expected, write):
    if write and not path.exists():
        with path.open("xb") as stream:
            stream.write(expected)
    if path.read_bytes() != expected:
        raise ValueError(f"unexpected file content: {path}")


def audit(source_gzip=None, write=False):
    checks = []

    def check(rule, condition, layer):
        if not condition:
            raise ValueError(f"{layer}: {rule}")
        checks.append({"rule": rule, "layer": layer, "status": "passed"})

    provenance = json.loads((CASE / "provenance.json").read_bytes())
    raw = (CASE / "input.json").read_bytes()
    if source_gzip is not None:
        compressed = source_gzip.read_bytes()
        check("gzip_hash_matches_collection_records",
              sha(compressed) == provenance["source_gzip_sha256"], "identity")
        unpacked = gzip.decompress(compressed)
        check("decompressed_source_hash_matches_provenance",
              sha(unpacked) == provenance["source_unpacked_sha256"], "identity")
        archived = json.loads(unpacked, parse_float=Decimal, object_pairs_hook=unique_keys,
                              parse_constant=reject_constant)
        current = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_keys,
                             parse_constant=reject_constant)
        check("input_values_and_order_match_archived_json",
              archived == current
              and json.loads(unpacked, object_pairs_hook=list, parse_float=Decimal)
                  == json.loads(raw, object_pairs_hook=list, parse_float=Decimal), "identity")
    check("input_sha256_matches_manifest", sha(raw) == provenance["input_sha256"], "identity")
    data = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_keys, parse_constant=reject_constant)
    check("strict_json_parse_unique_keys_and_finite_number_tokens", True, "structure")
    schema = json.loads(SCHEMA.read_bytes())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(raw))
    check("structural_schema_draft_2020_12", True, "structure")
    license_bytes = data["LICENSE"].encode("utf-8")
    check("embedded_license_and_source_present",
          bool(data["LICENSE"]) and bool(data["SOURCE"]), "identity")
    verify_or_create(CASE / "LICENSE.txt", license_bytes, write)
    check("license_copy_byte_for_byte", True, "identity")

    genera…1976 tokens truncated…son.json",
        "readme": "results/ucjl_orlib_10_0_1_w_native_v1/README.md",
        "full_candidates_distributed": false
      },
      "solver_code": "scripts/orlib10/solve_compare.py",
      "data_completeness": {
        "grade": "B",
        "reviewed_on": "2026-11-22",
        "basis": "明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用币种和价格年待核。",
        "evidence": "cases/ucjl_orlib_10_0_1_w_native_v1/README.md"
      }
    },
    {
      "case_id": "orlib_20_0_1_w",
      "path": "cases/orlib_20_0_1_w",
      "n_generator_records": 20,
      "n_buses": 1,
      "n_physical_branches": 0,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "classification": "lossless_input_reorganization",
      "data_quality": "source_values_preserved_with_profile_boundaries",
      "validation_report": "reports/orlib_20_0_1_w/package_validation.json",
      "model_execution": "copt_8.0.7_project_profile",
      "solve_status": "time_limit_with_verified_feasible_solution",
      "independent_solution_check": "passed",
      "verified_sample_count": 1,
      "pending_sample_count": 0,
      "results": {
        "directory": "results/orlib_20_0_1_w",
        "summary": "results/orlib_20_0_1_w/reference_results.csv",
        "verification": "results/orlib_20_0_1_w/verification.json",
        "readme": "results/orlib_20_0_1_w/README.md",
        "target_relative_gap": 0.00001,
        "achieved_relative_gap": 0.0008693708813969019,
        "full_candidates_distributed": false
      },
      "distribution_version": "1.0.2",
      "profile": "orlib_flat_audited_defaults_uc_v1",
      "family": "single_bus_uc",
      "checksum_manifest": "reports/orlib_20_0_1_w/checksums.sha256",
      "data_completeness": {
        "grade": "B",
        "reviewed_on": "2026-11-22",
        "basis": "明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用价格年待核。",
        "evidence": "cases/orlib_20_0_1_w/README.md"
      }
    },
    {
      "case_id": "orlib_50_0_1_w",
      "path": "cases/orlib_50_0_1_w",
      "n_generator_records": 50,
      "n_buses": 1,
      "n_physical_branches": 0,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "classification": "lossless_input_reorganization",
      "data_quality": "source_values_preserved_with_profile_boundaries",
      "validation_report": "reports/orlib_50_0_1_w/package_validation.json",
      "model_execution": "copt_8.0.7_project_profile",
      "solve_status": "optimal_within_declared_solver_tolerances",
      "independent_solution_check": "passed",
      "verified_sample_count": 1,
      "pending_sample_count": 0,
      "results": {
        "directory": "results/orlib_50_0_1_w",
        "summary": "results/orlib_50_0_1_w/reference_results.csv",
        "verification": "results/orlib_50_0_1_w/verification.json",
        "readme": "results/orlib_50_0_1_w/README.md",
        "target_relative_gap": 0.0001,
        "achieved_relative_gap": 0.0000996002385679896,
        "full_candidates_distributed": false
      },
      "distribution_version": "1.0.2",
      "profile": "orlib_flat_audited_defaults_uc_v1",
      "family": "single_bus_uc",
      "checksum_manifest": "reports/orlib_50_0_1_w/checksums.sha256",
      "data_completeness": {
        "grade": "B",
        "reviewed_on": "2026-11-22",
        "basis": "明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用价格年待核。",
        "evidence": "cases/orlib_50_0_1_w/README.md"
      }
    },
    {
      "case_id": "rpglab_ieee24_native_v1",
      "path": "cases/rpglab_ieee24_native_v1",
      "n_generator_records": 15,
      "n_buses": 24,
      "n_physical_branches": 38,
      "sample_count": 1800,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "classification": "lossless_input_reorganization",
      "data_quality": "source_inputs_preserved_with_open_metadata_and_model_issues",
      "validation_report": "reports/rpglab_ieee24_native_v1/data_validation.json",
      "model_execution": "verified_for_all_1800_samples",
      "solve_status": "completed_all_requested_samples",
      "independent_solution_check": "passed_for_all_1800_candidates",
      "verified_sample_count": 1800,
      "pending_sample_count": 0,
      "solver_status_counts": {
        "optimal_within_declared_solver_tolerances": 1800
      },
      "results": {
        "directory": "results/rpglab_ieee24_native_v1",
        "summary": "results/rpglab_ieee24_native_v1/reference_results.csv",
        "verification": "results/rpglab_ieee24_native_v1/verification.json",
        "readme": "results/rpglab_ieee24_native_v1/README.md",
        "target_relative_gap": 0.0001,
        "max_relative_gap": 0.000099635698976145,
        "full_candidates_distributed": false
      },
      "schema_version": "1.1.1",
      "distribution_version": "1.0.0",
      "profile": "rpglab-ieee24-native/1.0.0",
      "family": "network_uc",
      "checksum_manifest": "reports/rpglab_ieee24_native_v1/checksums.sha256",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "费用币种和价格年、备用响应时长口径及线路工程基准待核。",
        "evidence": "cases/rpglab_ieee24_native_v1/README.md"
      }
    },
    {
      "case_id": "opentepes_rts24_full_inputs_v1",
      "path": "cases/opentepes_rts24_full_inputs_v1",
      "n_generator_records": 33,
      "n_buses": 24,
      "n_physical_branches": 38,
      "scenario_count": 1,
      "stage_count": 1,
      "source_hour_count": 8736,
      "source_time_step_hours": 1,
      "effective_period_count_from_source_rules": 4368,
      "model_time_step_hours_from_source_rules": 2,
      "classification": "fixed_source_reference_and_full_horizon_input_audit",
      "data_quality": "input_checks_passed_with_open_source_intent_and_model_issues",
      "source_provenance": "cases/opentepes_rts24_full_inputs_v1/provenance.json",
      "validation_report": "reports/opentepes_rts24_full_inputs_v1/data_validation.json",
      "model_execution": "not_run",
      "copt_compatibility": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "distribution_version": "1.0.0",
      "profile": "opentepes-rts24-source-input-audit/1.0.0",
      "family": "network_uc",
      "checksum_manifest": "reports/opentepes_rts24_full_inputs_v1/checksums.sha256",
      "base_system_relationship": {
        "shares_network_topology_with": "rpglab_ieee24_native_v1",
        "basis": "Undirected endpoint multiset matches all 38 branches after node-number offset 100; retains a separate case/profile."
      },
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "爬坡和最小开停时间原栏为空，冷热启动分档及部分转换参数的来源意图待核。",
        "evidence": "cases/opentepes_rts24_full_inputs_v1/README.md"
      }
    },
    {
      "case_id": "rpglab_ieee24_legacy33_inputs_v1",
      "path": "cases/rpglab_ieee24_legacy33_inputs_v1",
      "n_generator_records": 33,
      "n_buses": 24,
      "n_physical_branches": 38,
      "sample_count": 1500,
      "source_columns_per_sample": 576,
      "time_mapping_status": "UNVERIFIED_candidate",
      "classification": "lossless_selected_input_reorganization",
      "family": "network_uc_inputs",
      "profile": "rpglab-ieee24-legacy33-inputs/1.0.0",
      "schema_version": null,
      "distribution_version": "1.0.0",
      "data_quality": "selected_input_tokens_independently_preserved_with_open_semantic_issues",
      "validation_report": "reports/rpglab_ieee24_legacy33_inputs_v1/data_validation.json",
      "independent_input_review": "reports/rpglab_ieee24_legacy33_inputs_v1/independent_review.json",
      "solve_status": "not_run",
      "model_execution": "not_run",
      "checksum_manifest": "reports/rpglab_ieee24_legacy33_inputs_v1/checksums.sha256",
      "data_completeness": {
        "grade": "D",
        "reviewed_on": "2026-11-22",
        "basis": "旧模型、时间映射、单位和初末边界待核。",
        "evidence": "cases/rpglab_ieee24_legacy33_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc10_inputs_v1",
      "path": "cases/kazarlis1996_uc10_inputs_v1",
      "input_file": "cases/kazarlis1996_uc10_inputs_v1/input.json",
      "n_generator_records": 10,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "base_input_transcription",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 1,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc10_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc10_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc10_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc20_inputs_v1",
      "path": "cases/kazarlis1996_uc20_inputs_v1",
      "input_file": "cases/kazarlis1996_uc20_inputs_v1/input.json",
      "n_generator_records": 20,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "expanded_from_base_by_user_specified_replication_rule",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 2,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc20_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc20_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc20_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc40_inputs_v1",
      "path": "cases/kazarlis1996_uc40_inputs_v1",
      "input_file": "cases/kazarlis1996_uc40_inputs_v1/input.json",
      "n_generator_records": 40,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "expanded_from_base_by_user_specified_replication_rule",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 4,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc40_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc40_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc40_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc60_inputs_v1",
      "path": "cases/kazarlis1996_uc60_inputs_v1",
      "input_file": "cases/kazarlis1996_uc60_inputs_v1/input.json",
      "n_generator_records": 60,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "expanded_from_base_by_user_specified_replication_rule",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 6,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc60_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc60_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc60_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc80_inputs_v1",
      "path": "cases/kazarlis1996_uc80_inputs_v1",
      "input_file": "cases/kazarlis1996_uc80_inputs_v1/input.json",
      "n_generator_records": 80,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "expanded_from_base_by_user_specified_replication_rule",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 8,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc80_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc80_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc80_inputs_v1/README.md"
      }
    },
    {
      "case_id": "kazarlis1996_uc100_inputs_v1",
      "path": "cases/kazarlis1996_uc100_inputs_v1",
      "input_file": "cases/kazarlis1996_uc100_inputs_v1/input.json",
      "n_generator_records": 100,
      "sample_count": 1,
      "horizon_per_sample": 24,
      "time_step_hours": 1,
      "family": "system_aggregate_uc_inputs",
      "benchmark_family": "kazarlis1996",
      "profile": "kazarlis1996-table-inputs/0.1.0",
      "schema_version": "0.1.0",
      "schema_path": "schema/kazarlis1996-table-inputs-0.1.0.schema.json",
      "distribution_version": "1.0.0",
      "classification": "expanded_from_base_by_user_specified_replication_rule",
      "network_parameters_status": "NOT_PROVIDED_IN_CURRENT_TABLE",
      "copy_factor": 10,
      "base_case_id": "kazarlis1996_uc10_inputs_v1",
      "data_quality": "source_values_preserved_with_explicit_table_gaps",
      "validation_report": "reports/kazarlis1996_uc100_inputs_v1/data_validation.json",
      "checksum_manifest": "reports/kazarlis1996_uc100_inputs_v1/checksums.sha256",
      "model_execution": "not_run",
      "solve_status": "not_run",
      "independent_solution_check": "not_run",
      "redistribution_permission": "UNVERIFIED",
      "data_completeness": {
        "grade": "C",
        "reviewed_on": "2026-11-22",
        "basis": "当前表未提供爬坡、初始出力、冷热切换规则和末端边界。",
        "evidence": "cases/kazarlis1996_uc100_inputs_v1/README.md"
      }
    }
  ],
  "catalog_version": "1.3.0",
  "system_count_note": "基础系统按可识别的独立电网统计。IEEE24 原版、旧 33 记录版和 openTEPES RTS24 为同一 IEEE RTS 24 节点基础系统下的不同算例。OR-LIB 三个单节点算例另记为一个基准系列，不计作物理电网。 Kazarlis六规模另记为1个系统级火电UC文献基准家族，不增加物理电网计数；复制倍数不代表独立系统。"
}

# Test Coverage Gap Analysis

Generated: analyze_coverage.py

## Modules Without Test Files

### ai.code_quality.analyzer

- **File**: `code_quality/analyzer.py`
- **Missing test**: `tests/test_analyzer.py`
- **Functions** (1): analyze_findings

### ai.code_quality.formatter

- **File**: `code_quality/formatter.py`
- **Missing test**: `tests/test_formatter.py`
- **Functions** (1): format_results

### ai.code_quality.models

- **File**: `code_quality/models.py`
- **Missing test**: `tests/test_models.py`
- **Functions** (4): error_count, warning_count, info_count, total_count
- **Classes** (3): Severity, LintFinding, LintSummary

### ai.code_quality.runner

- **File**: `code_quality/runner.py`
- **Missing test**: `tests/test_runner.py`
- **Functions** (1): run_all

### ai.gaming.models

- **File**: `gaming/models.py`
- **Missing test**: `tests/test_models.py`
- **Functions** (8): to_dict, to_dict, to_dict, from_dict, vram_pressure_pct, ram_pressure_pct, to_context_string, to_dict
- **Classes** (7): FrametimeStats, ThermalStats, LoadStats, GameSession, PerformanceIssue, GameProfile, HardwareSnapshot

### ai.log_intel.anomalies

- **File**: `log_intel/anomalies.py`
- **Missing test**: `tests/test_anomalies.py`
- **Functions** (7): check_anomalies, detect_anomalies, store_anomalies, update_status_file, get_unacknowledged, acknowledge, run_checks

### ai.log_intel.ingest

- **File**: `log_intel/ingest.py`
- **Missing test**: `tests/test_ingest.py`
- **Functions** (17): get_ingest_state, save_ingest_state, find_new_files, parse_health_log, parse_scan_log, parse_freshclam_log, ingest_health, ingest_scans, ingest_freshclam, ingest_all, main, embed_texts, health_trend, scan_history, get_anomalies, search_logs, pipeline_stats

### ai.log_intel.queries

- **File**: `log_intel/queries.py`
- **Missing test**: `tests/test_queries.py`
- **Functions** (5): health_trend, scan_history, get_anomalies, search_logs, pipeline_stats

### ai.mcp_bridge.server

- **File**: `mcp_bridge/server.py`
- **Missing test**: `tests/test_server.py`
- **Functions** (2): async health_check, create_app

### ai.mcp_bridge.tools

- **File**: `mcp_bridge/tools.py`
- **Missing test**: `tests/test_tools.py`
- **Functions** (1): async execute_tool

### ai.threat_intel.formatters

- **File**: `threat_intel/formatters.py`
- **Missing test**: `tests/test_formatters.py`
- **Functions** (2): format_html_section, format_single_row

### ai.threat_intel.lookup

- **File**: `threat_intel/lookup.py`
- **Missing test**: `tests/test_lookup.py`
- **Functions** (5): lookup_hash, lookup_hashes, main, decorator, wrapper
- **Classes** (1): LookupTimeoutError

### ai.threat_intel.models

- **File**: `threat_intel/models.py`
- **Missing test**: `tests/test_models.py`
- **Functions** (2): to_jsonl, has_data
- **Classes** (1): ThreatReport

### ai.threat_intel.playbooks

- **File**: `threat_intel/playbooks.py`
- **Missing test**: `tests/test_playbooks.py`
- **Functions** (3): get_response_plan, main, to_dict
- **Classes** (2): ActionStep, RecommendedAction

### ai.threat_intel.summary

- **File**: `threat_intel/summary.py`
- **Missing test**: `tests/test_summary.py`
- **Functions** (2): build_summary, main

### ai.utils.freshness

- **File**: `utils/freshness.py`
- **Missing test**: `tests/test_freshness.py`
- **Functions** (4): stamp_generated_at, parse_generated_at, format_freshness_age, read_json_with_freshness


## Detailed Coverage Data

```json
[
  {
    "module": "ai.agents.code_quality_agent",
    "file": "agents/code_quality_agent.py",
    "test_file": "test_code_quality_agent.py",
    "status": "HAS_TESTS",
    "functions": [
      "run_code_check"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_clean_output",
        "test_with_errors",
        "test_timeout_returns_error",
        "test_clean_output",
        "test_low_only_is_clean",
        "test_high_severity_not_clean",
        "test_clean_repo",
        "test_dirty_repo",
        "test_git_failure_returns_clean",
        "test_parses_collected_count",
        "test_failure_returns_zero",
        "test_all_clean_returns_clean",
        "test_ruff_errors_returns_warnings",
        "test_bandit_high_returns_issues",
        "test_bandit_medium_returns_warnings",
        "test_many_modified_returns_warnings",
        "test_many_untracked_returns_warnings",
        "test_full_workflow_writes_report",
        "test_report_keys_complete",
        "test_clean_when_all_nominal",
        "test_git_includes_last_commits",
        "test_report_includes_deps_key",
        "test_missing_script_returns_ok",
        "test_script_failure_adds_recommendation",
        "test_timeout_returns_ok"
      ],
      "test_classes": [
        "TestRunRuff",
        "TestRunBandit",
        "TestRunGitStatus",
        "TestRunPytestCollect",
        "TestBuildRecommendations",
        "TestRunCodeCheck",
        "TestDepCheck"
      ],
      "imports": [
        "_run_ruff",
        "_run_ruff",
        "_run_ruff",
        "_run_bandit",
        "_run_bandit",
        "_run_bandit",
        "_run_git_status",
        "_run_git_status",
        "_run_git_status",
        "_run_pytest_collect",
        "_run_pytest_collect",
        "_build_recommendations",
        "run_code_check",
        "_run_dep_check",
        "_build_recommendations",
        "_run_dep_check"
      ]
    }
  },
  {
    "module": "ai.agents.knowledge_storage",
    "file": "agents/knowledge_storage.py",
    "test_file": "test_knowledge_storage.py",
    "status": "HAS_TESTS",
    "functions": [
      "run_storage_check"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_nominal",
        "test_lancedb_not_installed",
        "test_connect_exception",
        "test_parses_last_ingest",
        "test_missing_file_returns_none",
        "test_no_timestamp_key",
        "test_parses_du_output",
        "test_failure_returns_zeros",
        "test_running_with_nomic",
        "test_running_without_nomic",
        "test_not_running",
        "test_all_nominal_returns_healthy",
        "test_empty_db_returns_attention",
        "test_stale_docs_returns_stale",
        "test_stale_logs_returns_stale",
        "test_ollama_down_returns_attention",
        "test_nomic_missing_returns_attention",
        "test_lancedb_error_returns_attention",
        "test_full_workflow_writes_report",
        "test_report_keys_complete",
        "test_healthy_when_all_nominal"
      ],
      "test_classes": [
        "TestCheckLancedb",
        "TestReadIngestState",
        "TestGetVectorDbSize",
        "TestCheckOllama",
        "TestBuildRecommendations",
        "TestRunStorageCheck"
      ],
      "imports": [
        "_check_lancedb",
        "_check_lancedb",
        "_check_lancedb",
        "_read_ingest_state",
        "_read_ingest_state",
        "_read_ingest_state",
        "_get_vector_db_size",
        "_get_vector_db_size",
        "_check_ollama",
        "_check_ollama",
        "_check_ollama",
        "_build_recommendations",
        "run_storage_check"
      ]
    }
  },
  {
    "module": "ai.agents.performance_tuning",
    "file": "agents/performance_tuning.py",
    "test_file": "test_performance_tuning.py",
    "status": "HAS_TESTS",
    "functions": [
      "run_tuning"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_nominal_temps",
        "test_sensors_failure_returns_zeros",
        "test_invalid_json_returns_zeros",
        "test_parses_nvidia_smi_output",
        "test_nvidia_smi_failure_returns_unavailable",
        "test_parses_free_output",
        "test_failure_returns_zeros",
        "test_parses_df_output_with_steam",
        "test_steam_not_mounted_skips",
        "test_all_nominal_returns_optimal",
        "test_hot_cpu_returns_attention",
        "test_hot_gpu_returns_attention",
        "test_high_memory_returns_attention",
        "test_heavy_swap_returns_attention",
        "test_home_disk_nearly_full_returns_attention",
        "test_steam_disk_nearly_full_returns_attention",
        "test_high_load_returns_attention",
        "test_minor_disk_returns_acceptable",
        "test_gpu_unavailable_message",
        "test_full_workflow_writes_report",
        "test_report_keys_complete",
        "test_gpu_unavailable_handled"
      ],
      "test_classes": [
        "TestCollectCpuTemps",
        "TestCollectGpuStats",
        "TestCollectMemory",
        "TestCollectDisk",
        "TestBuildRecommendations",
        "TestRunTuning"
      ],
      "imports": [
        "_collect_cpu_temps",
        "_collect_cpu_temps",
        "_collect_cpu_temps",
        "_collect_gpu_stats",
        "_collect_gpu_stats",
        "_collect_memory",
        "_collect_memory",
        "_collect_disk",
        "_collect_disk",
        "_build_recommendations",
        "run_tuning"
      ]
    }
  },
  {
    "module": "ai.agents.security_audit",
    "file": "agents/security_audit.py",
    "test_file": "test_security_audit.py",
    "status": "HAS_TESTS",
    "functions": [
      "run_audit"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_no_files_returns_false",
        "test_recent_file_returns_true",
        "test_old_file_returns_false",
        "test_picks_most_recent_file",
        "test_success_returns_true",
        "test_nonzero_exit_returns_false",
        "test_exception_returns_false",
        "test_triggers_when_stale",
        "test_skips_triggers_when_recent",
        "test_status_issues_on_threat_keywords",
        "test_status_warnings_on_warning_keywords",
        "test_report_written_atomically",
        "test_ingest_failure_sets_flag_false",
        "test_rag_failure_sets_fallback_message"
      ],
      "test_classes": [
        "TestRanRecently",
        "TestTriggerSystemctl",
        "TestRunAudit"
      ],
      "imports": [
        "_ran_recently",
        "_ran_recently",
        "_ran_recently",
        "_ran_recently",
        "_trigger_systemctl",
        "_trigger_systemctl",
        "_trigger_systemctl",
        "run_audit",
        "run_audit",
        "run_audit",
        "run_audit",
        "run_audit",
        "run_audit",
        "run_audit"
      ]
    }
  },
  {
    "module": "ai.cache",
    "file": "cache.py",
    "test_file": "test_cache.py",
    "status": "HAS_TESTS",
    "functions": [
      "get_cache_stats",
      "__init__",
      "get",
      "set",
      "delete",
      "clear",
      "stats",
      "evict_expired"
    ],
    "classes": [
      "JsonFileCache"
    ],
    "test_coverage": {
      "test_functions": [
        "test_set_and_get",
        "test_get_missing_key",
        "test_delete_existing",
        "test_delete_missing",
        "test_ttl_expiration",
        "test_ttl_zero_skips_write",
        "test_evict_expired",
        "test_atomic_write_no_partial_files",
        "test_clear_removes_all",
        "test_clear_empty_cache",
        "test_stats_keys_present",
        "test_stats_counts_entries",
        "test_hit_miss_counters",
        "test_hit_rate_zero_when_no_calls",
        "test_directory_sharding",
        "test_corrupt_json_handled",
        "test_thread_safety",
        "test_no_pickle_import"
      ],
      "test_classes": [
        "TestBasicOperations",
        "TestExpiry",
        "TestAtomicWrite",
        "TestClear",
        "TestStats",
        "TestHitMissCounters",
        "TestDirectorySharding",
        "TestCorruptHandling",
        "TestThreadSafety",
        "TestNoPickle"
      ],
      "imports": [
        "JsonFileCache"
      ]
    }
  },
  {
    "module": "ai.code_quality.analyzer",
    "file": "code_quality/analyzer.py",
    "test_file": "test_analyzer.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "analyze_findings"
    ],
    "classes": []
  },
  {
    "module": "ai.code_quality.formatter",
    "file": "code_quality/formatter.py",
    "test_file": "test_formatter.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "format_results"
    ],
    "classes": []
  },
  {
    "module": "ai.code_quality.models",
    "file": "code_quality/models.py",
    "test_file": "test_models.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "error_count",
      "warning_count",
      "info_count",
      "total_count"
    ],
    "classes": [
      "Severity",
      "LintFinding",
      "LintSummary"
    ]
  },
  {
    "module": "ai.code_quality.runner",
    "file": "code_quality/runner.py",
    "test_file": "test_runner.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "run_all"
    ],
    "classes": []
  },
  {
    "module": "ai.config",
    "file": "config.py",
    "test_file": "test_config.py",
    "status": "HAS_TESTS",
    "functions": [
      "load_keys",
      "get_key",
      "setup_logging"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_all_are_path_objects",
        "test_keys_env_path",
        "test_rate_limits_state_path",
        "test_project_structure",
        "test_load_keys_missing_file",
        "test_load_keys_exists",
        "test_get_key_returns_none_for_missing",
        "test_get_key_returns_none_for_empty",
        "test_get_key_returns_value",
        "test_load_keys_no_scope_loads_all",
        "test_load_keys_scope_llm",
        "test_load_keys_scope_threat_intel",
        "test_load_keys_invalid_scope_raises",
        "test_load_keys_scope_missing_file",
        "test_key_scopes_dict_has_expected_scopes",
        "test_key_scopes_llm_contains_expected_keys",
        "test_key_scopes_threat_intel_contains_expected_keys",
        "test_scoped_load_does_not_set_keys_loaded_flag",
        "test_setup_logging_returns_logger",
        "test_setup_logging_sets_level",
        "test_app_name",
        "test_version"
      ],
      "test_classes": [
        "TestPathConstants",
        "TestKeyLoading",
        "TestScopedKeyLoading",
        "TestLogging",
        "TestConstants"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.gaming.hardware",
    "file": "gaming/hardware.py",
    "test_file": "test_hardware.py",
    "status": "HAS_TESTS",
    "functions": [
      "get_hardware_snapshot"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_nvidia_smi_parsed",
        "test_nvidia_smi_na_values",
        "test_nvidia_smi_not_found",
        "test_nvidia_smi_timeout",
        "test_nvidia_smi_nonzero_exit",
        "test_nvidia_smi_short_output",
        "test_cpuinfo_parsed",
        "test_cpuinfo_unreadable",
        "test_cpuinfo_no_physical_id",
        "test_meminfo_parsed",
        "test_meminfo_unreadable",
        "test_zramctl_parsed",
        "test_zramctl_not_found",
        "test_zramctl_timeout",
        "test_zramctl_nonzero_exit",
        "test_gigabytes",
        "test_megabytes",
        "test_kilobytes",
        "test_bytes",
        "test_fractional",
        "test_empty",
        "test_invalid",
        "test_full_snapshot",
        "test_vram_pressure_pct",
        "test_vram_pressure_zero_total",
        "test_ram_pressure_pct",
        "test_to_context_string",
        "test_to_dict_structure",
        "test_partial_failure"
      ],
      "test_classes": [
        "TestGPUInfo",
        "TestCPUInfo",
        "TestMemoryInfo",
        "TestZRAMInfo",
        "TestParseSize",
        "TestHardwareSnapshot"
      ],
      "imports": [
        "(",
        "HardwareSnapshot"
      ]
    }
  },
  {
    "module": "ai.gaming.mangohud",
    "file": "gaming/mangohud.py",
    "test_file": "test_mangohud.py",
    "status": "HAS_TESTS",
    "functions": [
      "parse_mangohud_log",
      "analyze_performance",
      "suggest_optimizations"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_parse_basic_csv",
        "test_parse_fps_stats",
        "test_parse_frametime_stats",
        "test_parse_thermal_stats",
        "test_parse_load_stats",
        "test_parse_duration",
        "test_parse_game_name_from_comment",
        "test_parse_missing_columns",
        "test_parse_empty_file",
        "test_parse_header_only",
        "test_parse_bad_rows_skipped",
        "test_parse_file_not_found",
        "test_no_issues_clean_session",
        "test_gpu_thermal_critical",
        "test_cpu_thermal_critical",
        "test_vram_pressure_warning",
        "test_stutter_warning",
        "test_low_fps",
        "test_multiple_issues_sorted",
        "test_thermal_throttle_csv",
        "test_llm_suggestions_returned",
        "test_rate_limited_returns_static",
        "test_llm_failure_returns_static",
        "test_prime_offload_filtered",
        "test_empty_issues_no_llm_call"
      ],
      "test_classes": [
        "TestMangoHudParsing",
        "TestPerformanceAnalysis",
        "TestSuggestOptimizations"
      ],
      "imports": [
        "(",
        "("
      ]
    }
  },
  {
    "module": "ai.gaming.models",
    "file": "gaming/models.py",
    "test_file": "test_models.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "to_dict",
      "to_dict",
      "to_dict",
      "from_dict",
      "vram_pressure_pct",
      "ram_pressure_pct",
      "to_context_string",
      "to_dict"
    ],
    "classes": [
      "FrametimeStats",
      "ThermalStats",
      "LoadStats",
      "GameSession",
      "PerformanceIssue",
      "GameProfile",
      "HardwareSnapshot"
    ]
  },
  {
    "module": "ai.gaming.scopebuddy",
    "file": "gaming/scopebuddy.py",
    "test_file": "test_scopebuddy.py",
    "status": "HAS_TESTS",
    "functions": [
      "scan_steam_library",
      "list_profiles",
      "get_preset",
      "get_profile",
      "save_profile",
      "suggest_launch_options",
      "apply_mangohud_preset"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_parse_libraryfolders",
        "test_parse_nested_keys",
        "test_parse_empty_string",
        "test_parse_malformed",
        "test_scan_finds_games",
        "test_scan_no_library_found",
        "test_scan_skips_bad_acf",
        "test_scan_explicit_path",
        "test_scan_discovers_from_vdf",
        "test_get_profile_exists",
        "test_get_profile_missing",
        "test_get_profile_case_insensitive",
        "test_save_profile_creates_file",
        "test_save_profile_updates_existing",
        "test_get_profile_file_missing",
        "test_llm_suggestion",
        "test_rate_limited_safe_default",
        "test_prime_offload_filtered",
        "test_scaffold_response_returns_default",
        "test_router_exception_returns_default",
        "test_all_banned_lines_yields_default",
        "test_hardware_context_included",
        "test_rate_limiter_records_call",
        "test_apply_default_preset",
        "test_apply_full_preset",
        "test_apply_fps_only_preset",
        "test_invalid_preset_raises",
        "test_config_file_created",
        "test_preset_overwrites_existing",
        "test_preset_header_comment",
        "test_removes_prime_offload",
        "test_removes_dri_prime",
        "test_clean_text_unchanged",
        "test_empty_input"
      ],
      "test_classes": [
        "TestVDFParser",
        "TestSteamScanner",
        "TestGameProfiles",
        "TestSuggestLaunchOptions",
        "TestMangoHudPresets",
        "TestFilterBanned"
      ],
      "imports": [
        "GameProfile",
        "HardwareSnapshot",
        "("
      ]
    }
  },
  {
    "module": "ai.health",
    "file": "health.py",
    "test_file": "test_health.py",
    "status": "HAS_TESTS",
    "functions": [
      "__init__",
      "score",
      "is_disabled",
      "effective_score",
      "__init__",
      "get",
      "record_success",
      "record_failure",
      "get_sorted",
      "reset_all",
      "reset_all_scores"
    ],
    "classes": [
      "AllProvidersExhausted",
      "ProviderHealth",
      "HealthTracker"
    ],
    "test_coverage": {
      "test_functions": [
        "test_cold_start_score_is_half",
        "test_perfect_score",
        "test_all_failures_score_near_zero",
        "test_high_latency_penalizes_score",
        "test_is_disabled_when_disabled_until_in_future",
        "test_is_not_disabled_when_disabled_until_in_past",
        "test_is_not_disabled_when_none",
        "test_record_success_updates_counts",
        "test_record_failure_increments_consecutive",
        "test_success_resets_consecutive_failures",
        "test_auto_demotion_after_five_failures",
        "test_exponential_backoff_on_repeated_demotion",
        "test_backoff_caps_at_ten_minutes",
        "test_get_creates_new_provider",
        "test_get_sorted_returns_by_score_descending",
        "test_auth_broken_set_on_401",
        "test_auth_broken_set_on_403",
        "test_auth_broken_not_set_on_generic_error",
        "test_auth_broken_cleared_on_success",
        "test_get_sorted_excludes_disabled",
        "test_reset_all_scores",
        "test_reset_clears_cooldowns"
      ],
      "test_classes": [
        "TestProviderHealth",
        "TestHealthTracker"
      ],
      "imports": [
        "HealthTracker",
        "ProviderHealth"
      ]
    }
  },
  {
    "module": "ai.key_manager",
    "file": "key_manager.py",
    "test_file": "test_key_manager.py",
    "status": "HAS_TESTS",
    "functions": [
      "list_keys",
      "get_key_status",
      "write_status_file",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_returns_all_expected_keys",
        "test_set_key_reported_as_set",
        "test_empty_value_reported_as_missing",
        "test_absent_key_reported_as_missing",
        "test_missing_file_all_missing",
        "test_comments_and_blank_lines_ignored",
        "test_unknown_keys_not_included",
        "test_values_only_set_or_missing",
        "test_write_status_file_called_as_side_effect",
        "test_required_keys_in_result",
        "test_all_present_flags_true",
        "test_partial_llm_keys_flags_false",
        "test_missing_keys_list_populated",
        "test_empty_env_all_flags_false",
        "test_writes_valid_json",
        "test_no_tmp_files_left",
        "test_values_not_in_output_file",
        "test_summary_flags_in_file",
        "test_no_arg_reads_keys_env_fresh",
        "test_list_prints_json",
        "test_status_exits_1_when_keys_missing",
        "test_status_exits_0_when_all_keys_present",
        "test_list_output_has_no_secret_values",
        "test_default_command_is_list"
      ],
      "test_classes": [
        "TestListKeys",
        "TestGetKeyStatus",
        "TestWriteStatusFile",
        "TestCLI"
      ],
      "imports": [
        "_ALL_EXPECTED_KEYS",
        "list_keys",
        "list_keys",
        "list_keys",
        "list_keys",
        "list_keys",
        "list_keys",
        "_ALL_EXPECTED_KEYS",
        "list_keys",
        "list_keys",
        "list_keys",
        "get_key_status",
        "_ALL_EXPECTED_KEYS",
        "get_key_status",
        "get_key_status",
        "get_key_status",
        "get_key_status",
        "write_status_file",
        "write_status_file",
        "list_keys",
        "write_status_file",
        "write_status_file",
        "main",
        "main",
        "_ALL_EXPECTED_KEYS",
        "main",
        "main",
        "main"
      ]
    }
  },
  {
    "module": "ai.llm_proxy",
    "file": "llm_proxy.py",
    "test_file": "test_llm_proxy.py",
    "status": "HAS_TESTS",
    "functions": [
      "create_app",
      "main",
      "async chat_completions",
      "async list_models",
      "async health"
    ],
    "classes": [
      "AllProvidersExhausted"
    ],
    "test_coverage": {
      "test_functions": [
        "test_non_streaming_request",
        "test_streaming_request",
        "test_streaming_error_sends_graceful_chunk",
        "test_model_name_mapping",
        "test_invalid_json_request",
        "test_empty_messages_array",
        "test_exhaustion_returns_graceful_response",
        "test_router_error_returns_500",
        "test_conversation_memory_injection",
        "test_memory_retrieval_failure_graceful",
        "test_list_models",
        "test_health_check",
        "test_assert_localhost_accepts_valid",
        "test_assert_localhost_rejects_external",
        "test_write_llm_status_creates_file",
        "test_write_llm_status_graceful_failure"
      ],
      "test_classes": [
        "TestChatCompletions",
        "TestModelsEndpoint",
        "TestHealthEndpoint",
        "TestLocalhostBinding",
        "TestStatusWriter"
      ],
      "imports": [
        "create_app",
        "create_app",
        "AllProvidersExhausted",
        "create_app",
        "_assert_localhost",
        "_assert_localhost",
        "_write_llm_status",
        "_write_llm_status"
      ]
    }
  },
  {
    "module": "ai.log_intel.anomalies",
    "file": "log_intel/anomalies.py",
    "test_file": "test_anomalies.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "check_anomalies",
      "detect_anomalies",
      "store_anomalies",
      "update_status_file",
      "get_unacknowledged",
      "acknowledge",
      "run_checks"
    ],
    "classes": []
  },
  {
    "module": "ai.log_intel.ingest",
    "file": "log_intel/ingest.py",
    "test_file": "test_ingest.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "get_ingest_state",
      "save_ingest_state",
      "find_new_files",
      "parse_health_log",
      "parse_scan_log",
      "parse_freshclam_log",
      "ingest_health",
      "ingest_scans",
      "ingest_freshclam",
      "ingest_all",
      "main",
      "embed_texts",
      "health_trend",
      "scan_history",
      "get_anomalies",
      "search_logs",
      "pipeline_stats"
    ],
    "classes": []
  },
  {
    "module": "ai.log_intel.queries",
    "file": "log_intel/queries.py",
    "test_file": "test_queries.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "health_trend",
      "scan_history",
      "get_anomalies",
      "search_logs",
      "pipeline_stats"
    ],
    "classes": []
  },
  {
    "module": "ai.mcp_bridge.server",
    "file": "mcp_bridge/server.py",
    "test_file": "test_server.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "async health_check",
      "create_app"
    ],
    "classes": []
  },
  {
    "module": "ai.mcp_bridge.tools",
    "file": "mcp_bridge/tools.py",
    "test_file": "test_tools.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "async execute_tool"
    ],
    "classes": []
  },
  {
    "module": "ai.rag.chunker",
    "file": "rag/chunker.py",
    "test_file": "test_chunker.py",
    "status": "HAS_TESTS",
    "functions": [
      "chunk_scan_log",
      "chunk_health_log",
      "chunk_file",
      "chunk_enriched_jsonl"
    ],
    "classes": [
      "LogChunk"
    ],
    "test_coverage": {
      "test_functions": [
        "test_sections_detected",
        "test_timestamp_extracted",
        "test_detection_grouping",
        "test_summary_content",
        "test_log_type_is_scan",
        "test_source_file_set",
        "test_empty_log_returns_empty",
        "test_no_found_lines_no_detections_section",
        "test_found_lines_not_duplicated_in_summary",
        "test_sections_detected",
        "test_equals_delimiter_detected",
        "test_timestamp_extracted",
        "test_log_type_is_health",
        "test_section_content",
        "test_empty_log_returns_empty",
        "test_empty_section_filtered",
        "test_scan_detected_by_path",
        "test_health_detected_by_path",
        "test_scan_detected_by_content",
        "test_health_detected_by_content",
        "test_unknown_fallback",
        "test_empty_file_returns_empty",
        "test_file_not_found_raises",
        "test_source_file_populated",
        "test_parses_all_lines",
        "test_fields_populated",
        "test_content_generated",
        "test_uuid_generated",
        "test_vector_empty",
        "test_malformed_lines_skipped",
        "test_empty_lines_skipped",
        "test_file_not_found_raises",
        "test_missing_fields_default"
      ],
      "test_classes": [
        "TestChunkScanLog",
        "TestChunkHealthLog",
        "TestChunkFile",
        "TestChunkEnrichedJsonl"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.rag.code_query",
    "file": "rag/code_query.py",
    "test_file": "test_code_query.py",
    "status": "HAS_TESTS",
    "functions": [
      "code_rag_query"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_index_not_built_returns_message",
        "test_context_only_mode_returns_results",
        "test_llm_synthesis_mode",
        "test_scaffold_response_fallback",
        "test_func",
        "test_llm_routing_error_fallback",
        "test_func",
        "test_limit_parameter_respected",
        "test_empty_search_results",
        "test_missing_fields_in_search_results",
        "test_embed_single_error_propagates",
        "test_context_formatting"
      ],
      "test_classes": [
        "TestCodeRagQuery",
        "TestEdgeCases",
        "TestSystemPrompt"
      ],
      "imports": [
        "code_rag_query"
      ]
    }
  },
  {
    "module": "ai.rag.embedder",
    "file": "rag/embedder.py",
    "test_file": "test_embedder.py",
    "status": "HAS_TESTS",
    "functions": [
      "is_ollama_available",
      "embed_texts",
      "select_provider",
      "embed_single"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_available_exact_name",
        "test_available_with_tag",
        "test_unavailable_wrong_model",
        "test_unavailable_server_down",
        "test_successful_embedding",
        "test_multiple_texts",
        "test_model_not_found",
        "test_server_down",
        "test_successful_embedding",
        "test_no_api_key",
        "test_rate_limited",
        "test_input_type_forwarded",
        "test_gemini_primary_path",
        "test_cohere_fallback_when_gemini_fails",
        "test_ollama_emergency_when_both_cloud_fail",
        "test_all_unavailable_raises",
        "test_empty_input_returns_empty",
        "test_does_not_call_cohere_when_gemini_works",
        "test_returns_single_vector"
      ],
      "test_classes": [
        "TestIsOllamaAvailable",
        "TestEmbedOllama",
        "TestEmbedCohere",
        "TestEmbedTexts",
        "TestEmbedSingle"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.rag.ingest_code",
    "file": "rag/ingest_code.py",
    "test_file": "test_ingest_code.py",
    "status": "HAS_TESTS",
    "functions": [
      "discover_python_files",
      "chunk_python_file",
      "ingest_files",
      "ingest_repo",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_finds_py_files",
        "test_excludes_venv",
        "test_excludes_pycache",
        "test_exclude_dirs_constant_covers_expected_dirs",
        "test_returns_sorted",
        "test_module_with_no_defs",
        "test_splits_on_functions",
        "test_splits_on_class",
        "test_header_prepended_to_chunks",
        "test_line_numbers_are_1_indexed",
        "test_oversized_chunk_is_truncated",
        "test_all_chunks_have_required_metadata_keys",
        "test_indented_methods_not_split",
        "test_processes_py_file",
        "test_oversized_file_skipped",
        "test_unchanged_file_skipped_by_mtime",
        "test_doc_count_cap",
        "test_summary_dict_keys",
        "test_non_py_files_ignored"
      ],
      "test_classes": [
        "TestDiscoverPythonFiles",
        "TestChunkPythonFile",
        "TestIngestFiles"
      ],
      "imports": [
        "MAX_BYTES_PER_DOC",
        "MAX_DOCS_PER_RUN",
        "("
      ]
    }
  },
  {
    "module": "ai.rag.ingest_docs",
    "file": "rag/ingest_docs.py",
    "test_file": "test_ingest_docs.py",
    "status": "HAS_TESTS",
    "functions": [
      "chunk_markdown",
      "ingest_files",
      "ingest_directory",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_oversized_file_is_skipped",
        "test_exactly_at_limit_is_allowed",
        "test_summary_includes_skipped_size",
        "test_stops_at_max_docs_per_run",
        "test_deferred_count_in_summary",
        "test_stops_at_total_bytes_limit",
        "test_all_expected_keys_present",
        "test_unchanged_files_counted",
        "test_non_md_files_not_counted",
        "test_save_state_retries_on_io_error",
        "test_save_state_succeeds_first_try"
      ],
      "test_classes": [
        "TestFileSizeCap",
        "TestDocCountCap",
        "TestTotalBytesCap",
        "TestSummaryDict",
        "TestSaveStateRetry"
      ],
      "imports": [
        "MAX_BYTES_PER_DOC",
        "MAX_DOCS_PER_RUN",
        "MAX_TOTAL_BYTES",
        "ingest_files",
        "_file_hash",
        "_save_state",
        "_save_state"
      ]
    }
  },
  {
    "module": "ai.rag.memory",
    "file": "rag/memory.py",
    "test_file": "test_memory.py",
    "status": "HAS_TESTS",
    "functions": [
      "is_enabled",
      "store_interaction",
      "retrieve_relevant_context"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_false_when_not_set",
        "test_false_when_set_to_false",
        "test_true_when_set_to_true",
        "test_case_insensitive",
        "test_no_op_when_disabled",
        "test_creates_row_and_returns_true",
        "test_query_truncated_to_500_chars",
        "test_response_summary_truncated_to_200_chars",
        "test_embed_failure_returns_false",
        "test_calls_cleanup_after_add",
        "test_returns_empty_when_disabled",
        "test_returns_summaries_from_search_results",
        "test_empty_summary_fields_filtered_out",
        "test_table_error_returns_empty",
        "test_uses_search_query_input_type",
        "test_no_cleanup_under_limit",
        "test_no_cleanup_at_exact_limit",
        "test_cleanup_triggered_over_limit",
        "test_cleanup_deletes_oldest_first",
        "test_to_arrow_error_does_not_raise",
        "test_filters_system_prompt_content",
        "test_filters_knowledge_tool_names",
        "test_filters_section_dividers",
        "test_allows_normal_conversation"
      ],
      "test_classes": [
        "TestIsEnabled",
        "TestStoreInteraction",
        "TestRetrieveRelevantContext",
        "TestCleanupIfNeeded",
        "TestContentFiltering"
      ],
      "imports": [
        "(  # noqa: E402",
        "I001"
      ]
    }
  },
  {
    "module": "ai.rag.query",
    "file": "rag/query.py",
    "test_file": "test_query.py",
    "status": "HAS_TESTS",
    "functions": [
      "rag_query",
      "format_result"
    ],
    "classes": [
      "QueryResult"
    ],
    "test_coverage": {
      "test_functions": [
        "test_defaults",
        "test_custom_values",
        "test_empty_chunks",
        "test_log_chunk_formatting",
        "test_threat_chunk_formatting",
        "test_chunk_without_source_uses_hash",
        "test_multiple_chunks_separated",
        "test_chunk_without_distance",
        "test_contains_system_context",
        "test_contains_context_section",
        "test_contains_question",
        "test_only_context_instruction",
        "test_text_format",
        "test_text_no_sources",
        "test_json_format",
        "test_json_is_valid",
        "test_full_pipeline_with_llm",
        "test_context_only_mode",
        "test_scaffold_fallback",
        "test_empty_results",
        "test_llm_error_fallback",
        "test_results_sorted_by_distance",
        "test_sources_deduplicated",
        "test_threat_source_uses_hash",
        "test_search_failure_graceful"
      ],
      "test_classes": [
        "TestQueryResult",
        "TestBuildContext",
        "TestBuildPrompt",
        "TestFormatResult",
        "TestRagQuery"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.rag.store",
    "file": "rag/store.py",
    "test_file": "test_store.py",
    "status": "HAS_TESTS",
    "functions": [
      "get_store",
      "__init__",
      "add_log_chunks",
      "add_doc_chunks",
      "add_code_chunks",
      "search_code",
      "add_threat_reports",
      "search_logs",
      "search_docs",
      "search_threats",
      "count"
    ],
    "classes": [
      "VectorStore"
    ],
    "test_coverage": {
      "test_functions": [
        "test_default_path",
        "test_custom_path",
        "test_lazy_connection",
        "test_connect_called_once",
        "test_add_chunks",
        "test_add_multiple_chunks",
        "test_add_empty_list",
        "test_generates_id_if_missing",
        "test_add_failure_returns_zero",
        "test_creates_table_if_missing",
        "test_add_reports",
        "test_add_empty_list",
        "test_generates_id_if_missing",
        "test_add_failure_returns_zero",
        "test_creates_table_if_missing",
        "test_search_returns_results",
        "test_search_empty_results",
        "test_search_failure_returns_empty",
        "test_search_returns_results",
        "test_search_respects_limit",
        "test_search_failure_returns_empty",
        "test_count_existing_table",
        "test_count_missing_table",
        "test_count_failure_returns_zero",
        "test_returns_vector_store",
        "test_singleton_same_instance"
      ],
      "test_classes": [
        "TestVectorStoreInit",
        "TestAddLogChunks",
        "TestAddThreatReports",
        "TestSearchLogs",
        "TestSearchThreats",
        "TestCount",
        "TestGetStore"
      ],
      "imports": [
        "VectorStore",
        "get_store  # noqa: E402"
      ]
    }
  },
  {
    "module": "ai.rate_limiter",
    "file": "rate_limiter.py",
    "test_file": "test_rate_limiter.py",
    "status": "HAS_TESTS",
    "functions": [
      "__init__",
      "can_call",
      "record_call",
      "wait_time"
    ],
    "classes": [
      "RateLimiter"
    ],
    "test_coverage": {
      "test_functions": [
        "test_loads_all_providers",
        "test_missing_definitions_file",
        "test_fresh_state_allows_call",
        "test_unknown_provider_allowed",
        "test_creates_state_file",
        "test_increments_counters",
        "test_blocks_after_limit",
        "test_window_reset",
        "test_blocks_after_hourly_limit",
        "test_hourly_window_reset",
        "test_wait_time_positive_when_rph_blocked",
        "test_null_rph_unconstrained",
        "test_backward_compat_no_hourly_fields",
        "test_blocks_after_daily_limit",
        "test_daily_reset",
        "test_null_rpm_unconstrained",
        "test_null_rpd_unconstrained",
        "test_zero_when_can_call",
        "test_positive_when_rpm_blocked",
        "test_zero_for_unknown_provider",
        "test_state_written_atomically",
        "test_concurrent_writes"
      ],
      "test_classes": [
        "TestLoadDefinitions",
        "TestCanCall",
        "TestRecordCall",
        "TestRpmEnforcement",
        "TestRphEnforcement",
        "TestRpdEnforcement",
        "TestNullLimits",
        "TestWaitTime",
        "TestAtomicWrite",
        "TestConcurrentSafety"
      ],
      "imports": [
        "RateLimiter"
      ]
    }
  },
  {
    "module": "ai.router",
    "file": "router.py",
    "test_file": "test_router.py",
    "status": "HAS_TESTS",
    "functions": [
      "get_cost_stats",
      "reset_cost_stats",
      "get_usage_stats",
      "reset_usage_stats",
      "route_query",
      "async route_chat",
      "async route_query_stream",
      "get_health_snapshot",
      "reset_router",
      "reset_health_scores"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_invalid_task_type",
        "test_valid_task_types_tuple",
        "test_standard_model",
        "test_no_slash",
        "test_multiple_slashes",
        "test_empty_config_raises",
        "test_empty_model_list_raises",
        "test_keys_loaded_before_router",
        "test_completion_returns_text",
        "test_completion_passes_kwargs",
        "test_completion_uses_correct_model_name",
        "test_embedding_returns_json",
        "test_embedding_empty_data",
        "test_all_providers_limited_raises",
        "test_records_call_after_success",
        "test_api_error_raises_runtime",
        "test_timeout_raises_runtime",
        "test_reset_clears_state",
        "test_get_usage_stats_structure",
        "test_counters_increment_after_route_query",
        "test_reset_usage_stats_zeros_everything",
        "test_json_file_cache_is_instance",
        "test_litellm_cache_is_none",
        "test_cache_dir_path",
        "test_repeated_identical_calls_return_same_result"
      ],
      "test_classes": [
        "TestValidation",
        "TestExtractProvider",
        "TestRouterInit",
        "TestCompletion",
        "TestEmbedding",
        "TestRateLimiting",
        "TestErrorHandling",
        "TestReset",
        "TestUsageTracking",
        "TestDiskCache"
      ],
      "imports": [
        "JsonFileCache",
        "("
      ]
    }
  },
  {
    "module": "ai.system.fedora_updates",
    "file": "system/fedora_updates.py",
    "test_file": "test_fedora_updates.py",
    "status": "HAS_TESTS",
    "functions": [
      "check_updates",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_extracts_alias_and_type",
        "test_date_truncated_to_10_chars",
        "test_url_constructed_from_alias",
        "test_packages_extracted_from_builds",
        "test_security_updates_separated",
        "test_non_security_not_in_security_list",
        "test_critical_count_accurate",
        "test_relevant_updates_match_installed_rpms",
        "test_uninstalled_non_security_excluded",
        "test_rpm_failure_returns_empty_set",
        "test_bodhi_down_returns_empty_report",
        "test_rate_limited_skips_fetch",
        "test_404_returns_empty_updates",
        "test_report_written_atomically",
        "test_cli_calls_check_updates"
      ],
      "test_classes": [
        "TestParseUpdate",
        "TestSecurityFilter",
        "TestRpmMatching",
        "TestGracefulDegradation",
        "TestCLI"
      ],
      "imports": [
        "_parse_update",
        "_parse_update",
        "_parse_update",
        "_parse_update",
        "check_updates",
        "check_updates",
        "check_updates",
        "check_updates",
        "check_updates",
        "_get_installed_rpms",
        "check_updates",
        "check_updates",
        "check_updates",
        "check_updates",
        "main"
      ]
    }
  },
  {
    "module": "ai.system.pkg_intel",
    "file": "system/pkg_intel.py",
    "test_file": "test_pkg_intel.py",
    "status": "HAS_TESTS",
    "functions": [
      "lookup_package",
      "scan_requirements",
      "mcp_handler",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_latest_version_detected",
        "test_outdated_version_detected",
        "test_license_extracted",
        "test_source_repo_extracted",
        "test_no_advisories",
        "test_none_data_returns_safe_defaults",
        "test_advisory_keys_extracted",
        "test_provenance_detected",
        "test_no_provenance_when_absent",
        "test_parses_pinned_requirements",
        "test_ignores_comments_and_options",
        "test_scan_queries_each_package",
        "test_scan_report_written",
        "test_deps_dev_down_skips_package",
        "test_404_returns_none",
        "test_rate_limited_skips_fetch",
        "test_can_call_checked_before_request",
        "test_record_call_after_success",
        "test_returns_latest_report",
        "test_no_report_returns_error_dict",
        "test_single_package_cli",
        "test_scan_cli"
      ],
      "test_classes": [
        "TestExtractPackageInfo",
        "TestAdvisoryExtraction",
        "TestScanMode",
        "TestGracefulDegradation",
        "TestRateLimiterIntegration",
        "TestMcpHandler",
        "TestCLI"
      ],
      "imports": [
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_extract_package_info",
        "_parse_requirements",
        "_parse_requirements",
        "scan_requirements",
        "scan_requirements",
        "scan_requirements",
        "_fetch_package",
        "_fetch_package",
        "_fetch_version",
        "_fetch_version",
        "mcp_handler",
        "mcp_handler",
        "main",
        "main"
      ]
    }
  },
  {
    "module": "ai.system.release_watch",
    "file": "system/release_watch.py",
    "test_file": "test_release_watch.py",
    "status": "HAS_TESTS",
    "functions": [
      "check_releases",
      "main"
    ],
    "classes": [],
    "test_coverage": {
      "test_functions": [
        "test_parses_tag_and_date",
        "test_404_returns_none",
        "test_rate_limited_returns_none",
        "test_request_error_returns_none",
        "test_summary_truncated_to_200_chars",
        "test_token_added_to_headers_when_set",
        "test_returns_advisory_count",
        "test_404_returns_zero",
        "test_request_error_returns_zero",
        "test_advisory_count_in_check_releases_output",
        "test_update_available_when_tag_changed",
        "test_no_update_when_tag_unchanged",
        "test_first_run_update_available_is_false",
        "test_github_down_skips_repo_continues_others",
        "test_returns_summary_dict",
        "test_rate_limiter_checked_before_request",
        "test_record_call_after_successful_request",
        "test_cli_calls_check_releases",
        "test_cli_single_repo_flag"
      ],
      "test_classes": [
        "TestFetchLatestRelease",
        "TestFetchAdvisories",
        "TestUpdateAvailableDetection",
        "TestGracefulDegradation",
        "TestRateLimiterIntegration",
        "TestCLI"
      ],
      "imports": [
        "_fetch_latest_release",
        "_fetch_latest_release",
        "_fetch_latest_release",
        "_fetch_latest_release",
        "_fetch_latest_release",
        "_fetch_latest_release",
        "_fetch_advisories",
        "_fetch_advisories",
        "_fetch_advisories",
        "check_releases",
        "check_releases",
        "check_releases",
        "check_releases",
        "check_releases",
        "check_releases",
        "_fetch_latest_release",
        "_fetch_latest_release",
        "main",
        "main"
      ]
    }
  },
  {
    "module": "ai.threat_intel.correlator",
    "file": "threat_intel/correlator.py",
    "test_file": "test_correlator.py",
    "status": "HAS_TESTS",
    "functions": [
      "correlate_ioc",
      "main",
      "to_dict",
      "has_correlations"
    ],
    "classes": [
      "LinkedIOC",
      "CorrelationReport"
    ],
    "test_coverage": {
      "test_functions": [
        "test_correlate_hash_with_valid_response",
        "test_correlate_hash_with_no_data",
        "test_correlate_ip_with_high_abuse_score",
        "test_correlate_url_malicious",
        "test_correlate_cve_critical",
        "test_correlate_cve_in_kev",
        "test_correlate_invalid_ioc_type",
        "test_correlate_network_timeout",
        "test_correlate_rate_limit_exceeded",
        "test_map_ransomware_tags_to_t1486",
        "test_map_trojan_tags_to_t1059",
        "test_map_high_abuse_ip_to_t1072",
        "test_map_critical_cve_to_t1190",
        "test_map_empty_metadata_returns_empty_list",
        "test_map_limits_to_five_techniques",
        "test_cve_critical_risk_cvss_9_plus",
        "test_cve_high_risk_cvss_7_to_9",
        "test_cve_medium_risk_cvss_4_to_7",
        "test_hash_critical_high_detection_ratio",
        "test_hash_high_detection_ratio_20_to_50_percent",
        "test_ip_high_confidence_above_80_percent",
        "test_url_malware_type_high_risk",
        "test_unknown_type_returns_unknown_risk",
        "test_malformed_detection_ratio_handled_gracefully",
        "test_report_to_dict_serialization",
        "test_has_correlations_property",
        "test_load_mitre_map_missing_file",
        "test_load_mitre_map_malformed_json",
        "test_concurrent_hash_correlations",
        "test_rate_limit_shared_across_correlations"
      ],
      "test_classes": [
        "TestCorrelateIOC",
        "TestMitreMapping",
        "TestRiskLevelCalculation",
        "TestCorrelationReportModel",
        "TestMitreMapLoading",
        "TestConcurrentCorrelation"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.threat_intel.cve_scanner",
    "file": "threat_intel/cve_scanner.py",
    "test_file": "test_cve_scanner.py",
    "status": "HAS_TESTS",
    "functions": [
      "enumerate_packages",
      "scan_cves",
      "main"
    ],
    "classes": [
      "PackageInfo",
      "CVEEntry",
      "ScanReport"
    ],
    "test_coverage": {
      "test_functions": [
        "test_parses_name_version",
        "test_empty_output_returns_empty",
        "test_subprocess_failure_returns_empty",
        "test_parses_tab_separated",
        "test_missing_flatpak_returns_empty",
        "test_parses_json_output",
        "test_invalid_json_returns_empty",
        "test_subprocess_failure_returns_empty",
        "test_parses_cve_id_and_severity",
        "test_rate_limited_returns_empty",
        "test_request_error_returns_empty",
        "test_404_returns_empty",
        "test_api_key_included_in_headers",
        "test_parses_cve_alias",
        "test_uses_ghsa_id_when_no_cve_alias",
        "test_request_error_returns_empty",
        "test_empty_vulns_returns_empty",
        "test_kev_flag_set_for_matching_cve",
        "test_stale_cache_triggers_fetch",
        "test_fetch_failure_uses_stale_cache",
        "test_no_cache_no_network_returns_empty",
        "test_report_written_atomically",
        "test_report_filename_contains_today",
        "test_returns_summary_dict",
        "test_no_packages_no_cves",
        "test_kev_cves_counted",
        "test_report_write_failure_does_not_raise",
        "test_deduplicates_cves",
        "test_summary_includes_kev_matches_and_osv_flag",
        "test_osv_called_when_nvd_empty_for_pip",
        "test_osv_not_called_when_nvd_has_results_for_pip",
        "test_osv_skipped_for_rpm_packages",
        "test_osv_down_skips_gracefully",
        "test_kev_sets_exploited_in_wild_and_due_date"
      ],
      "test_classes": [
        "TestEnumRpm",
        "TestEnumFlatpak",
        "TestEnumPip",
        "TestLookupNvd",
        "TestLookupOsv",
        "TestKevOverlay",
        "TestWriteReport",
        "TestScanCvesGraceful",
        "TestOsvFallback",
        "TestKevReportFields"
      ],
      "imports": [
        "_enum_rpm",
        "_enum_rpm",
        "_enum_rpm",
        "_enum_flatpak",
        "_enum_flatpak",
        "_enum_pip",
        "_enum_pip",
        "_enum_pip",
        "PackageInfo",
        "_lookup_nvd",
        "PackageInfo",
        "_lookup_nvd",
        "PackageInfo",
        "_lookup_nvd",
        "PackageInfo",
        "_lookup_nvd",
        "PackageInfo",
        "_lookup_nvd",
        "PackageInfo",
        "_lookup_osv",
        "PackageInfo",
        "_lookup_osv",
        "PackageInfo",
        "_lookup_osv",
        "PackageInfo",
        "_lookup_osv",
        "_load_kev_cache",
        "_load_kev_cache",
        "_load_kev_cache",
        "_load_kev_cache",
        "CVEEntry",
        "ScanReport",
        "_write_report",
        "ScanReport",
        "_write_report",
        "scan_cves",
        "scan_cves",
        "PackageInfo",
        "scan_cves",
        "scan_cves",
        "CVEEntry",
        "PackageInfo",
        "scan_cves",
        "scan_cves",
        "PackageInfo",
        "scan_cves",
        "CVEEntry",
        "PackageInfo",
        "scan_cves",
        "PackageInfo",
        "scan_cves",
        "PackageInfo",
        "scan_cves",
        "PackageInfo",
        "scan_cves"
      ]
    }
  },
  {
    "module": "ai.threat_intel.formatters",
    "file": "threat_intel/formatters.py",
    "test_file": "test_formatters.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "format_html_section",
      "format_single_row"
    ],
    "classes": []
  },
  {
    "module": "ai.threat_intel.ioc_lookup",
    "file": "threat_intel/ioc_lookup.py",
    "test_file": "test_ioc_lookup.py",
    "status": "HAS_TESTS",
    "functions": [
      "lookup_url",
      "main",
      "has_data",
      "to_json"
    ],
    "classes": [
      "IOCReport"
    ],
    "test_coverage": {
      "test_functions": [
        "test_valid_http",
        "test_valid_https_with_path",
        "test_valid_ftp",
        "test_strips_whitespace",
        "test_empty_rejected",
        "test_no_scheme_rejected",
        "test_file_scheme_rejected",
        "test_javascript_scheme_rejected",
        "test_no_netloc_rejected",
        "test_returns_dict_on_hit",
        "test_returns_none_on_no_results",
        "test_returns_none_on_invalid_url_status",
        "test_extracts_payload_hashes",
        "test_returns_none_when_rate_limited",
        "test_returns_none_on_request_error",
        "test_records_call_on_success",
        "test_returns_dict_on_hit",
        "test_returns_none_on_no_results",
        "test_returns_none_on_empty_data",
        "test_confidence_risk_mapping",
        "test_returns_none_when_rate_limited",
        "test_returns_none_on_request_error",
        "test_records_call_on_success",
        "test_returns_dict_on_hit",
        "test_returns_empty_on_404",
        "test_returns_empty_on_request_error",
        "test_handles_missing_fields_gracefully",
        "test_urlhaus_hit_returns_urlhaus_source",
        "test_urlhaus_miss_calls_threatfox",
        "test_urlhaus_hit_skips_threatfox",
        "test_circl_enrichment_when_urlhaus_has_hashes",
        "test_circl_capped_at_3_hashes",
        "test_circl_miss_excludes_from_source",
        "test_both_miss_returns_none_report",
        "test_invalid_url_returns_immediately",
        "test_circl_failure_doesnt_block_report",
        "test_threatfox_failure_graceful_degradation",
        "test_tags_deduplicated",
        "test_to_json_excludes_raw_data",
        "test_rate_limiter_blocks_urlhaus",
        "test_has_data_true_with_source",
        "test_has_data_false_when_source_none",
        "test_has_data_false_when_source_empty",
        "test_to_json_valid",
        "test_to_json_has_timestamp"
      ],
      "test_classes": [
        "TestValidateURL",
        "TestLookupURLhaus",
        "TestLookupThreatFox",
        "TestEnrichCIRL",
        "TestLookupURL",
        "TestIOCReport"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.threat_intel.ip_lookup",
    "file": "threat_intel/ip_lookup.py",
    "test_file": "test_ip_lookup.py",
    "status": "HAS_TESTS",
    "functions": [
      "lookup_ip",
      "main",
      "has_data",
      "to_json"
    ],
    "classes": [
      "IPReport"
    ],
    "test_coverage": {
      "test_functions": [
        "test_valid_public_ipv4",
        "test_valid_public_ipv6",
        "test_private_ipv4_rejected",
        "test_private_10_block_rejected",
        "test_loopback_rejected",
        "test_loopback_ipv6_rejected",
        "test_malformed_rejected",
        "test_empty_string_rejected",
        "test_strips_whitespace",
        "test_link_local_rejected",
        "test_returns_score_on_success",
        "test_returns_zero_score",
        "test_returns_none_when_rate_limited",
        "test_returns_none_when_no_key",
        "test_returns_none_on_request_error",
        "test_returns_none_when_score_missing",
        "test_records_call_on_success",
        "test_returns_malicious_classification",
        "test_returns_benign_classification",
        "test_returns_unknown_on_404",
        "test_returns_none_when_rate_limited",
        "test_returns_none_when_no_key",
        "test_returns_none_on_request_error",
        "test_returns_ports_and_vulns",
        "test_returns_empty_on_404",
        "test_returns_empty_on_request_error",
        "test_handles_missing_keys_gracefully",
        "test_score_80_block",
        "test_score_100_block",
        "test_score_50_malicious_greynoise",
        "test_score_79_malicious_greynoise",
        "test_score_50_benign_greynoise",
        "test_score_79_benign_greynoise",
        "test_score_50_no_greynoise_defaults_likely_malicious",
        "test_score_30_suspicious",
        "test_score_49_suspicious",
        "test_score_29_low_risk",
        "test_score_0_low_risk",
        "test_score_55_triggers_greynoise_and_applies",
        "test_score_29_skips_greynoise",
        "test_score_71_skips_greynoise",
        "test_score_70_triggers_greynoise",
        "test_valid_ip_with_all_providers",
        "test_private_ip_returns_none_report",
        "test_invalid_ip_returns_none_report",
        "test_abuseipdb_failure_graceful_degradation",
        "test_greynoise_failure_doesnt_block_report",
        "test_shodan_failure_doesnt_block_report",
        "test_report_includes_shodan_vulns",
        "test_source_includes_greynoise_when_queried",
        "test_to_json_valid_and_no_raw_data",
        "test_rate_limiter_respected"
      ],
      "test_classes": [
        "TestValidateIP",
        "TestLookupAbuseIPDB",
        "TestLookupGreyNoise",
        "TestEnrichShodan",
        "TestMakeRecommendation",
        "TestTiebreakerLogic",
        "TestLookupIP"
      ],
      "imports": [
        "("
      ]
    }
  },
  {
    "module": "ai.threat_intel.lookup",
    "file": "threat_intel/lookup.py",
    "test_file": "test_lookup.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "lookup_hash",
      "lookup_hashes",
      "main",
      "decorator",
      "wrapper"
    ],
    "classes": [
      "LookupTimeoutError"
    ]
  },
  {
    "module": "ai.threat_intel.models",
    "file": "threat_intel/models.py",
    "test_file": "test_models.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "to_jsonl",
      "has_data"
    ],
    "classes": [
      "ThreatReport"
    ]
  },
  {
    "module": "ai.threat_intel.playbooks",
    "file": "threat_intel/playbooks.py",
    "test_file": "test_playbooks.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "get_response_plan",
      "main",
      "to_dict"
    ],
    "classes": [
      "ActionStep",
      "RecommendedAction"
    ]
  },
  {
    "module": "ai.threat_intel.sandbox",
    "file": "threat_intel/sandbox.py",
    "test_file": "test_sandbox.py",
    "status": "HAS_TESTS",
    "functions": [
      "submit_file",
      "main",
      "to_json"
    ],
    "classes": [
      "SandboxReport"
    ],
    "test_coverage": {
      "test_functions": [
        "test_valid_file_in_quarantine",
        "test_rejects_traversal",
        "test_rejects_missing_file",
        "test_rejects_directory",
        "test_dotdot_in_path_rejected",
        "test_returns_cached_when_hash_found",
        "test_cached_does_not_submit",
        "test_submits_when_not_cached",
        "test_submission_includes_environment_id",
        "test_submission_uses_falcon_sandbox_useragent",
        "test_rate_limited_returns_rate_limited_status",
        "test_rate_limit_checked_before_network",
        "test_record_call_on_hash_search",
        "test_missing_api_key_returns_error",
        "test_invalid_path_returns_error",
        "test_hash_search_request_error_falls_through",
        "test_submission_rejected_400_returns_error",
        "test_sha256_computed_for_valid_file",
        "test_submit_network_error_returns_error"
      ],
      "test_classes": [
        "TestValidatePath",
        "TestHashFirst",
        "TestSubmissionFlow",
        "TestRateLimiter",
        "TestGracefulDegradation"
      ],
      "imports": [
        "_validate_path",
        "_validate_path",
        "_validate_path",
        "_validate_path",
        "_validate_path",
        "submit_file",
        "submit_file",
        "submit_file",
        "_ENVIRONMENT_ID",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file",
        "submit_file"
      ]
    }
  },
  {
    "module": "ai.threat_intel.summary",
    "file": "threat_intel/summary.py",
    "test_file": "test_summary.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "build_summary",
      "main"
    ],
    "classes": []
  },
  {
    "module": "ai.utils.freshness",
    "file": "utils/freshness.py",
    "test_file": "test_freshness.py",
    "status": "NO_TEST_FILE",
    "functions": [
      "stamp_generated_at",
      "parse_generated_at",
      "format_freshness_age",
      "read_json_with_freshness"
    ],
    "classes": []
  }
]
```

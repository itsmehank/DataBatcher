from src.real_estate.cli import build_parser


def test_cli_has_expected_commands():
    parser = build_parser()
    subparser_action = next(action for action in parser._actions if getattr(action, "choices", None) is not None)
    assert subparser_action.choices is not None
    subcommands = set(subparser_action.choices)

    assert "init-db" in subcommands
    assert "ingest" in subcommands
    assert "analyze" in subcommands
    assert "clean-anomalies" in subcommands
    assert "recalculate-derived" in subcommands
    assert "serve-web" in subcommands
    assert "validate-config" in subcommands


def test_cli_ingest_defaults_parse():
    parser = build_parser()
    args = parser.parse_args(["ingest"])
    assert hasattr(args, "start_ymd")
    assert hasattr(args, "end_ymd")

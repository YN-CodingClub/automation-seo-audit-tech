from __future__ import annotations

import pandas as pd
import pytest

from audit_engine import analyze_seo_data


def by_id(issues):
    return {issue.id: issue for issue in issues}


def test_analyze_seo_data_requires_url_column() -> None:
    df = pd.DataFrame({"Status Code": [200]})

    with pytest.raises(KeyError, match="Colonne URL introuvable"):
        analyze_seo_data(df)


def test_analyze_seo_data_excludes_p2_by_default_and_includes_when_enabled() -> None:
    df = pd.DataFrame({"Address": ["https://example.com/a"]})

    issues_default, _ = analyze_seo_data(df, include_advanced=False)
    issues_advanced, _ = analyze_seo_data(df, include_advanced=True)

    assert len(issues_default) == 34
    assert all(issue.tier != "P2" for issue in issues_default)
    assert len(issues_advanced) == 42
    assert {f"SEO-{number:03d}" for number in range(35, 43)} <= set(by_id(issues_advanced))


def test_missing_required_columns_returns_not_evaluable() -> None:
    df = pd.DataFrame({"Address": ["https://example.com/a"]})

    issues, _ = analyze_seo_data(df)
    issue = by_id(issues)["SEO-001"]

    assert issue.status == "not_evaluable"
    assert issue.count == 0
    assert issue.reason == "Colonnes manquantes: status_code"
    assert issue.recommandation == "Exporter les colonnes manquantes puis relancer l'audit."


def test_basic_rules_detect_status_title_h1_meta_canonical_and_duplicates(
    core_screaming_frog_df,
) -> None:
    issues, metadata = analyze_seo_data(core_screaming_frog_df)
    issues_by_id = by_id(issues)

    assert metadata["selected_scope_urls"] == 5
    assert issues_by_id["SEO-001"].count == 1
    assert issues_by_id["SEO-001"].percentage == 20.0
    assert issues_by_id["SEO-001"].priority == "Haute"
    assert issues_by_id["SEO-007"].count == 1
    assert issues_by_id["SEO-012"].count == 1
    assert issues_by_id["SEO-013"].count == 2
    assert issues_by_id["SEO-017"].count == 1
    assert issues_by_id["SEO-021"].count == 1
    assert issues_by_id["SEO-022"].count == 2


def test_canonical_target_rules_use_normalized_urls() -> None:
    df = pd.DataFrame(
        [
            {
                "Address": "https://example.com/source-404",
                "Content Type": "text/html",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Canonical Link Element 1": "https://example.com/target-404/#frag",
            },
            {
                "Address": "https://example.com/source-noindex",
                "Content Type": "text/html",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Canonical Link Element 1": "https://example.com/target-noindex/",
            },
            {
                "Address": "https://example.com/target-404",
                "Content Type": "text/html",
                "Status Code": 404,
                "Indexability": "Indexable",
                "Canonical Link Element 1": "https://example.com/target-404",
            },
            {
                "Address": "https://example.com/target-noindex",
                "Content Type": "text/html",
                "Status Code": 200,
                "Indexability": "Non-Indexable",
                "Canonical Link Element 1": "https://example.com/target-noindex",
            },
        ]
    )

    issues, _ = analyze_seo_data(df)
    issues_by_id = by_id(issues)

    assert issues_by_id["SEO-008"].status == "detected"
    assert issues_by_id["SEO-009"].count == 2
    assert issues_by_id["SEO-010"].count == 2


def test_image_scope_detects_only_image_urls_without_alt() -> None:
    df = pd.DataFrame(
        [
            {
                "Address": "https://example.com/image.png",
                "Content Type": "image/png",
                "Images Without Alt Count 1": 1,
            },
            {
                "Address": "https://example.com/page",
                "Content Type": "text/html",
                "Images Without Alt Count 1": 3,
            },
        ]
    )

    issues, _ = analyze_seo_data(df, scope_label="Tout le crawl")
    issue = by_id(issues)["SEO-034"]

    assert issue.scope == "Images"
    assert issue.count == 1
    assert issue.examples == ["https://example.com/image.png"]


def test_advanced_hreflang_rule_is_gated_by_include_advanced() -> None:
    df = pd.DataFrame(
        {
            "Address": ["https://example.com/fr"],
            "Content Type": ["text/html"],
            "Indexability": ["Indexable"],
            "Hreflang Code 1": ["fr"],
            "Hreflang Link 1": [""],
            "Hreflang Code 2": [""],
            "Hreflang Link 2": [""],
            "Hreflang Code 3": [""],
            "Hreflang Link 3": [""],
        }
    )

    issues_default, _ = analyze_seo_data(df, include_advanced=False)
    issues_advanced, _ = analyze_seo_data(df, include_advanced=True)

    assert "SEO-035" not in by_id(issues_default)
    issue = by_id(issues_advanced)["SEO-035"]
    assert issue.status == "detected"
    assert issue.count == 1

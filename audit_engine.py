from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import asdict, dataclass
from io import StringIO
from typing import Any, Literal

import pandas as pd

IssueStatus = Literal["detected", "ok", "not_evaluable"]
ScopeKey = Literal["HTML indexables", "Tout HTML", "Tout le crawl"]

SCOPE_LABELS: list[ScopeKey] = [
    "HTML indexables",
    "Tout HTML",
    "Tout le crawl",
]


CANONICAL_COLUMN_ALIASES: dict[str, list[str]] = {
    "url": ["Adresse", "Address", "URL", "Url"],
    "content_type": ["Type de contenu", "Content Type"],
    "status_code": ["Code HTTP", "Status Code", "Status"],
    "indexability": ["Indexabilité", "Indexability", "Indexable"],
    "indexability_status": ["Statut d'indexabilité", "Indexability Status"],
    "title_1": ["Title 1", "Title"],
    "title_1_len": ["Longueur du Title 1", "Title 1 Length", "Title Length"],
    "title_1_px": ["Largeur en pixels du Title 1", "Title 1 Pixel Width"],
    "meta_desc_1": ["Meta Description 1", "Meta Description"],
    "meta_desc_1_len": ["Longueur de la Meta Description 1", "Meta Description 1 Length"],
    "meta_desc_1_px": ["Largeur en pixels de la Meta Description 1", "Meta Description 1 Pixel Width"],
    "meta_desc_2": ["Meta Description 2"],
    "h1_1": ["H1-1", "H1 1", "H1"],
    "h1_2": ["H1-2", "H1 2"],
    "h2_1": ["H2-1", "H2 1"],
    "meta_robots_1": ["Meta Robots 1", "Meta Robots"],
    "x_robots_1": ["Balise X-Robots 1", "X-Robots-Tag 1", "X-Robots-Tag"],
    "canonical_1": [
        "Élément de lien en version canonique 1",
        "Canonical Link Element 1",
        "Canonical Link Element",
        "Canonical",
    ],
    "rel_next_1": ['rel="next" 1', 'Rel="Next" 1'],
    "rel_prev_1": ['rel="prev" 1', 'Rel="Prev" 1'],
    "word_count": ["Nombre de mots", "Word Count"],
    "text_ratio": ["Ratio texte", "Text Ratio"],
    "crawl_depth": ["Crawl profondeur", "Crawl Depth"],
    "folder_depth": ["Profondeur du dossier", "Folder Depth"],
    "link_score": ["Link Score"],
    "inlinks": ["Liens entrants", "Inlinks"],
    "outlinks": ["Liens sortants", "Outlinks"],
    "near_dup_count": ["Nombre de quasi-doublons", "Near Duplicates"],
    "response_time": ["Temps de réponse", "Response Time"],
    "images_without_alt": ["Images Without Alt Count 1", "Images Missing Alt Text"],
    "hreflang_code_1": ["Hreflang Code 1"],
    "hreflang_code_2": ["Hreflang Code 2"],
    "hreflang_code_3": ["Hreflang Code 3"],
    "hreflang_link_1": ["Hreflang Link 1"],
    "hreflang_link_2": ["Hreflang Link 2"],
    "hreflang_link_3": ["Hreflang Link 3"],
    "inspection_status": ["Statut de l'API d'inspection d'URL", "URL Inspection API Status"],
    "inspection_error": ["Erreur de l'API d'inspection d'URL", "URL Inspection API Error"],
    "user_canonical": [
        "Version canonique déclarée par l'utilisateur",
        "User-declared Canonical",
    ],
    "google_canonical": [
        "Version canonique sélectionnée par Google",
        "Google-selected Canonical",
    ],
    "mobile_ux_issues": ["Problèmes d'ergonomie mobile", "Mobile Usability Issues"],
    "rich_results_errors": [
        "Erreurs de type de résultats enrichis",
        "Rich Results Type Errors",
    ],
    "perf_score": ["Score de performance", "Performance Score"],
    "cwv_eval": ["Évaluation des Core Web Vitals", "Core Web Vitals Assessment"],
}

NUMERIC_COLUMNS = {
    "status_code",
    "title_1_len",
    "title_1_px",
    "meta_desc_1_len",
    "meta_desc_1_px",
    "word_count",
    "text_ratio",
    "crawl_depth",
    "folder_depth",
    "link_score",
    "inlinks",
    "outlinks",
    "near_dup_count",
    "response_time",
    "images_without_alt",
    "rich_results_errors",
    "perf_score",
}


@dataclass
class TicketDefinition:
    id: str
    tier: str
    category: str
    name: str
    complexity: str
    scope_mode: str
    required_columns: list[str]
    constat_suffix: str
    recommendation: str
    seo_explanation: str


@dataclass
class IssueRecord:
    id: str
    name: str
    category: str
    status: IssueStatus
    count: int
    percentage: float
    examples: list[str]
    priority: str
    complexity: str
    required_columns: list[str]
    reason: str
    scope: str
    tier: str
    constat: str
    recommandation: str
    explication_seo: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TICKETS: list[TicketDefinition] = [
    TicketDefinition(
        id="SEO-001",
        tier="P0",
        category="Crawl",
        name="Erreurs 4xx",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["status_code"],
        constat_suffix="renvoient un code HTTP 4xx.",
        recommendation="Corriger les liens internes cassés et rétablir les pages supprimées avec des 301 pertinentes.",
        seo_explanation="Les 4xx coupent les parcours utilisateurs et gaspillent du budget de crawl.",
    ),
    TicketDefinition(
        id="SEO-002",
        tier="P0",
        category="Crawl",
        name="Erreurs 5xx",
        complexity="Haute",
        scope_mode="selected",
        required_columns=["status_code"],
        constat_suffix="renvoient un code HTTP 5xx.",
        recommendation="Stabiliser l'infrastructure et corriger les endpoints en erreur pour éviter les indisponibilités.",
        seo_explanation="Les 5xx répétés peuvent provoquer une désindexation temporaire et un recul de crawl.",
    ),
    TicketDefinition(
        id="SEO-003",
        tier="P1",
        category="Crawl",
        name="Redirections temporaires (302/307)",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["status_code"],
        constat_suffix="utilisent une redirection temporaire (302/307).",
        recommendation="Remplacer les 302/307 permanentes par des 301 et pointer directement les liens internes vers la destination finale.",
        seo_explanation="Les redirections temporaires prolongées introduisent de la friction de crawl.",
    ),
    TicketDefinition(
        id="SEO-004",
        tier="P0",
        category="Indexation",
        name="Pages non indexables canonisées",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=["indexability", "indexability_status"],
        constat_suffix="sont non indexables avec un statut de canonisation.",
        recommendation="Valider que la canonisation est volontaire et qu'aucune page stratégique n'est exclue par erreur.",
        seo_explanation="Une mauvaise combinaison indexabilité/canonical peut exclure des pages utiles des SERP.",
    ),
    TicketDefinition(
        id="SEO-005",
        tier="P0",
        category="Indexation",
        name="Noindex détecté",
        complexity="Faible",
        scope_mode="html_only",
        required_columns=["meta_robots_1", "x_robots_1"],
        constat_suffix="contiennent une directive noindex.",
        recommendation="Retirer noindex des pages qui doivent générer du trafic SEO.",
        seo_explanation="Noindex bloque explicitement la présence de la page dans l'index.",
    ),
    TicketDefinition(
        id="SEO-006",
        tier="P1",
        category="Indexation",
        name="Nofollow forcé",
        complexity="Faible",
        scope_mode="html_only",
        required_columns=["meta_robots_1", "x_robots_1"],
        constat_suffix="contiennent une directive nofollow.",
        recommendation="Réserver nofollow aux cas justifiés et éviter de couper la propagation interne de signaux.",
        seo_explanation="Nofollow massif peut dégrader le maillage et la circulation d'autorité.",
    ),
    TicketDefinition(
        id="SEO-007",
        tier="P0",
        category="Canonical",
        name="Canonical manquante",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=["canonical_1"],
        constat_suffix="n'ont pas de canonical déclarée.",
        recommendation="Ajouter une canonical explicite sur les pages indexables.",
        seo_explanation="Canonical stabilise les signaux lorsque plusieurs variantes d'URL existent.",
    ),
    TicketDefinition(
        id="SEO-008",
        tier="P0",
        category="Canonical",
        name="Canonical non self-referencing",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=["url", "canonical_1"],
        constat_suffix="pointent vers une canonical différente de leur URL.",
        recommendation="Confirmer les canonicals croisées et revenir en self-canonical si ce n'est pas intentionnel.",
        seo_explanation="Une canonical non self peut déplacer les signaux vers une autre URL.",
    ),
    TicketDefinition(
        id="SEO-009",
        tier="P0",
        category="Canonical",
        name="Canonical cible non-200",
        complexity="Haute",
        scope_mode="html_only",
        required_columns=["url", "canonical_1", "status_code"],
        constat_suffix="pointent vers une canonical dont la cible n'est pas en 200.",
        recommendation="Corriger les canonicals pour pointer uniquement vers des cibles 200 stables.",
        seo_explanation="Une canonical vers une cible non valide rend le signal ambigu.",
    ),
    TicketDefinition(
        id="SEO-010",
        tier="P0",
        category="Canonical",
        name="Canonical cible non indexable",
        complexity="Haute",
        scope_mode="html_only",
        required_columns=["url", "canonical_1", "indexability"],
        constat_suffix="pointent vers une canonical non indexable.",
        recommendation="Rediriger la canonical vers une URL indexable de référence.",
        seo_explanation="Canonical vers une page non indexable peut neutraliser la valeur SEO de la source.",
    ),
    TicketDefinition(
        id="SEO-011",
        tier="P1",
        category="URL",
        name="URLs à paramètres indexables",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=["url", "indexability"],
        constat_suffix="sont indexables avec des paramètres d'URL.",
        recommendation="Consolider les paramètres via canonical/noindex ou règles de crawl.",
        seo_explanation="Les paramètres indexables multiplient les variantes et le risque de duplication.",
    ),
    TicketDefinition(
        id="SEO-012",
        tier="P0",
        category="Title",
        name="Titles manquants",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["title_1"],
        constat_suffix="n'ont pas de Title exploitable.",
        recommendation="Rédiger un title unique avec intention, mot-clé principal et bénéfice.",
        seo_explanation="Le title influence directement la compréhension thématique et le CTR.",
    ),
    TicketDefinition(
        id="SEO-013",
        tier="P0",
        category="Title",
        name="Titles dupliqués",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["title_1", "url"],
        constat_suffix="partagent un Title dupliqué.",
        recommendation="Différencier chaque title pour refléter l'unicité de chaque page.",
        seo_explanation="Les titles dupliqués augmentent la cannibalisation et brouillent la pertinence.",
    ),
    TicketDefinition(
        id="SEO-014",
        tier="P1",
        category="Title",
        name="Titles trop courts",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["title_1_len", "title_1"],
        constat_suffix="ont un Title trop court (<30 caractères).",
        recommendation="Étoffer les titles courts pour mieux expliciter la proposition de valeur.",
        seo_explanation="Un title trop court limite la précision sémantique envoyée aux moteurs.",
    ),
    TicketDefinition(
        id="SEO-015",
        tier="P1",
        category="Title",
        name="Titles trop longs",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["title_1_len", "title_1"],
        constat_suffix="ont un Title trop long (>60 caractères).",
        recommendation="Raccourcir les titles et placer l'information clé en début de chaîne.",
        seo_explanation="Les titres trop longs sont plus souvent tronqués en SERP.",
    ),
    TicketDefinition(
        id="SEO-016",
        tier="P1",
        category="Title",
        name="Titles trop larges (pixels)",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["title_1_px"],
        constat_suffix="dépassent la largeur recommandée (>580 px).",
        recommendation="Réduire la longueur visuelle des titles pour éviter la coupure.",
        seo_explanation="La largeur en pixels impacte l'affichage final du snippet.",
    ),
    TicketDefinition(
        id="SEO-017",
        tier="P0",
        category="H1",
        name="H1 manquants",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["h1_1"],
        constat_suffix="n'ont pas de H1.",
        recommendation="Ajouter un H1 unique descriptif aligné sur le title.",
        seo_explanation="Le H1 structure le sujet principal de la page.",
    ),
    TicketDefinition(
        id="SEO-018",
        tier="P1",
        category="H1",
        name="H1 dupliqués",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["h1_1", "url"],
        constat_suffix="partagent un H1 identique.",
        recommendation="Rendre chaque H1 spécifique à la page.",
        seo_explanation="Des H1 identiques réduisent la différenciation entre URLs.",
    ),
    TicketDefinition(
        id="SEO-019",
        tier="P1",
        category="H1",
        name="H1 multiples",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["h1_2"],
        constat_suffix="contiennent un second H1.",
        recommendation="Conserver un seul H1 principal et déplacer le reste en H2/H3.",
        seo_explanation="Un balisage heading ambigu complique la hiérarchie du contenu.",
    ),
    TicketDefinition(
        id="SEO-020",
        tier="P1",
        category="H2",
        name="H2 manquants",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["h2_1"],
        constat_suffix="n'ont pas de H2.",
        recommendation="Structurer les sections principales avec des H2 explicites.",
        seo_explanation="Les H2 renforcent la lisibilité et la compréhension des sous-thèmes.",
    ),
    TicketDefinition(
        id="SEO-021",
        tier="P0",
        category="Meta",
        name="Meta descriptions manquantes",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["meta_desc_1"],
        constat_suffix="n'ont pas de meta description.",
        recommendation="Rédiger une meta description unique orientée intention + CTA.",
        seo_explanation="La meta description influence fortement le CTR organique.",
    ),
    TicketDefinition(
        id="SEO-022",
        tier="P1",
        category="Meta",
        name="Meta descriptions dupliquées",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["meta_desc_1", "url"],
        constat_suffix="partagent une meta description dupliquée.",
        recommendation="Personnaliser les descriptions pour éviter des snippets répétitifs.",
        seo_explanation="Des descriptions identiques réduisent la pertinence perçue par requête.",
    ),
    TicketDefinition(
        id="SEO-023",
        tier="P1",
        category="Meta",
        name="Meta descriptions trop courtes",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["meta_desc_1_len", "meta_desc_1"],
        constat_suffix="ont une meta description trop courte (<70).",
        recommendation="Allonger les descriptions courtes pour expliciter l'offre.",
        seo_explanation="Une description trop courte réduit la capacité à convaincre au clic.",
    ),
    TicketDefinition(
        id="SEO-024",
        tier="P1",
        category="Meta",
        name="Meta descriptions trop longues",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["meta_desc_1_len", "meta_desc_1"],
        constat_suffix="ont une meta description trop longue (>155).",
        recommendation="Raccourcir les descriptions pour éviter la troncature.",
        seo_explanation="La troncature réduit la lisibilité du snippet et la promesse utilisateur.",
    ),
    TicketDefinition(
        id="SEO-025",
        tier="P1",
        category="Meta",
        name="Meta descriptions multiples",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["meta_desc_2"],
        constat_suffix="contiennent une seconde meta description.",
        recommendation="Conserver une seule meta description canonique par page.",
        seo_explanation="Les signaux contradictoires peuvent rendre l'extraction de snippet instable.",
    ),
    TicketDefinition(
        id="SEO-026",
        tier="P0",
        category="Contenu",
        name="Thin content",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["word_count"],
        constat_suffix="ont un contenu court (<200 mots).",
        recommendation="Enrichir les contenus faibles avec information utile et structure éditoriale.",
        seo_explanation="Un contenu trop mince a plus de mal à couvrir l'intention de recherche.",
    ),
    TicketDefinition(
        id="SEO-027",
        tier="P1",
        category="Contenu",
        name="Ratio texte faible",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["text_ratio"],
        constat_suffix="ont un ratio texte faible (<10).",
        recommendation="Rééquilibrer la page en augmentant la part de contenu textuel utile.",
        seo_explanation="Un ratio texte trop bas peut signaler une valeur éditoriale insuffisante.",
    ),
    TicketDefinition(
        id="SEO-028",
        tier="P1",
        category="Contenu",
        name="Quasi-doublons",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["near_dup_count"],
        constat_suffix="présentent des quasi-doublons.",
        recommendation="Fusionner, différencier ou canonicaliser les contenus proches.",
        seo_explanation="Les quasi-doublons dispersent les signaux et favorisent la cannibalisation.",
    ),
    TicketDefinition(
        id="SEO-029",
        tier="P0",
        category="Architecture",
        name="Profondeur de crawl élevée",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["crawl_depth"],
        constat_suffix="sont trop profondes dans l'arborescence (>3).",
        recommendation="Rapprocher les pages stratégiques de la racine via maillage et navigation.",
        seo_explanation="Les pages profondes sont explorées moins fréquemment et transmettent moins de signaux.",
    ),
    TicketDefinition(
        id="SEO-030",
        tier="P1",
        category="Architecture",
        name="Faible maillage entrant",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["inlinks"],
        constat_suffix="ont un maillage entrant faible (<=1).",
        recommendation="Ajouter des liens internes contextuels depuis des pages fortes.",
        seo_explanation="Un faible nombre d'inlinks réduit la découvrabilité et la transmission d'autorité.",
    ),
    TicketDefinition(
        id="SEO-031",
        tier="P1",
        category="Architecture",
        name="Aucun lien sortant interne",
        complexity="Faible",
        scope_mode="selected",
        required_columns=["outlinks"],
        constat_suffix="n'ont aucun lien sortant interne.",
        recommendation="Ajouter des liens sortants internes pertinents pour fluidifier les parcours.",
        seo_explanation="Des pages isolées dans le maillage appauvrissent la navigation et le crawl.",
    ),
    TicketDefinition(
        id="SEO-032",
        tier="P1",
        category="Architecture",
        name="Link Score faible",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["link_score"],
        constat_suffix="ont un Link Score faible (<10).",
        recommendation="Renforcer l'autorité interne via des liens depuis des pages à forte valeur.",
        seo_explanation="Un Link Score faible peut limiter le potentiel de visibilité de la page.",
    ),
    TicketDefinition(
        id="SEO-033",
        tier="P1",
        category="Perf",
        name="Temps de réponse élevé",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["response_time"],
        constat_suffix="ont un temps de réponse élevé (>1s).",
        recommendation="Optimiser backend, cache et infrastructure pour réduire la latence serveur.",
        seo_explanation="La vitesse impacte le crawl et l'expérience utilisateur.",
    ),
    TicketDefinition(
        id="SEO-034",
        tier="P1",
        category="Media",
        name="Images sans ALT",
        complexity="Faible",
        scope_mode="image_only",
        required_columns=["images_without_alt"],
        constat_suffix="contiennent des images sans attribut ALT.",
        recommendation="Ajouter des ALT descriptifs orientés accessibilité et contexte sémantique.",
        seo_explanation="Les ALT aident l'accessibilité et renforcent les signaux image/search.",
    ),
    TicketDefinition(
        id="SEO-035",
        tier="P2",
        category="International",
        name="Hreflang incomplet",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=[
            "hreflang_code_1",
            "hreflang_code_2",
            "hreflang_code_3",
            "hreflang_link_1",
            "hreflang_link_2",
            "hreflang_link_3",
        ],
        constat_suffix="ont des codes hreflang sans lien correspondant.",
        recommendation="Aligner chaque code hreflang avec une URL cible valide.",
        seo_explanation="Un hreflang incomplet peut invalider l'interprétation linguistique.",
    ),
    TicketDefinition(
        id="SEO-036",
        tier="P2",
        category="International",
        name="x-default absent en multilingue",
        complexity="Moyenne",
        scope_mode="html_only",
        required_columns=["hreflang_code_1", "hreflang_code_2", "hreflang_code_3"],
        constat_suffix="sont multilingues sans x-default.",
        recommendation="Ajouter x-default quand plusieurs variantes linguistiques sont déclarées.",
        seo_explanation="x-default clarifie la page fallback pour les marchés non ciblés.",
    ),
    TicketDefinition(
        id="SEO-037",
        tier="P2",
        category="GSC API",
        name="Erreurs inspection URL",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["inspection_status", "inspection_error"],
        constat_suffix="présentent une erreur d'inspection URL API.",
        recommendation="Analyser les causes dans GSC et corriger les blocages d'indexation signalés.",
        seo_explanation="Les erreurs d'inspection révèlent des obstacles concrets de découverte/indexation.",
    ),
    TicketDefinition(
        id="SEO-038",
        tier="P2",
        category="GSC API",
        name="Canonical Google différente",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["user_canonical", "google_canonical"],
        constat_suffix="ont une canonical Google différente de la déclarée.",
        recommendation="Réduire les signaux contradictoires (maillage, duplication, canonicals).",
        seo_explanation="Un écart canonical user/Google indique un manque de confiance dans le signal fourni.",
    ),
    TicketDefinition(
        id="SEO-039",
        tier="P2",
        category="Mobile",
        name="Problèmes mobile UX",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["mobile_ux_issues"],
        constat_suffix="présentent des problèmes d'ergonomie mobile.",
        recommendation="Corriger les problèmes mobile remontés pour stabiliser l'expérience et le SEO mobile.",
        seo_explanation="Une expérience mobile dégradée affecte la qualité perçue des pages.",
    ),
    TicketDefinition(
        id="SEO-040",
        tier="P2",
        category="Rich Results",
        name="Erreurs résultats enrichis",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["rich_results_errors"],
        constat_suffix="ont des erreurs de résultats enrichis.",
        recommendation="Corriger les schémas en erreur pour restaurer l'éligibilité aux rich results.",
        seo_explanation="Les erreurs schema bloquent l'affichage enrichi en SERP.",
    ),
    TicketDefinition(
        id="SEO-041",
        tier="P2",
        category="CWV",
        name="Core Web Vitals en échec",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["cwv_eval"],
        constat_suffix="échouent l'évaluation Core Web Vitals.",
        recommendation="Prioriser les templates en échec et corriger LCP/INP/CLS.",
        seo_explanation="Les CWV sont un signal d'expérience utilisateur à maintenir dans la zone verte.",
    ),
    TicketDefinition(
        id="SEO-042",
        tier="P2",
        category="Perf",
        name="Score performance faible",
        complexity="Moyenne",
        scope_mode="selected",
        required_columns=["perf_score"],
        constat_suffix="ont un score de performance inférieur à 80.",
        recommendation="Optimiser ressources critiques (CSS/JS/images) et temps de rendu principal.",
        seo_explanation="Un faible score performance dégrade l'expérience et la découvrabilité.",
    ),
]


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in ascii_only.strip().lower() if ch.isalnum())


def decode_csv(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def detect_delimiter(sample: str) -> str:
    candidates = [",", ";", "\t", "|"]
    header_hints = {normalize_name(alias) for alias in ["Adresse", "Address", "Code HTTP", "Status Code", "Title 1", "H1-1"]}
    best_delimiter = ","
    best_score = -1
    for delimiter in candidates:
        score = 0
        for line in sample.splitlines()[:10]:
            cells = [cell for cell in line.split(delimiter) if cell.strip()]
            tokens = {normalize_name(cell) for cell in cells}
            score += max(len(cells) - 1, 0)
            score += sum(2 for hint in header_hints if hint in tokens)
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    if best_score > 0:
        return best_delimiter

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def detect_header_row(csv_text: str, delimiter: str, max_scan_rows: int = 10) -> int:
    hints = {normalize_name(alias) for alias in ["Adresse", "Address", "Code HTTP", "Status Code", "Title 1", "H1-1"]}
    best_index = 0
    best_score = -1

    lines = csv_text.splitlines()[:max_scan_rows]
    reader = csv.reader(lines, delimiter=delimiter)
    for idx, row in enumerate(reader):
        tokens = {normalize_name(cell) for cell in row if str(cell).strip()}
        score = 0
        for hint in hints:
            if hint in tokens:
                score += 2
            elif any(hint in token for token in tokens):
                score += 1
        if score > best_score:
            best_score = score
            best_index = idx

    return best_index if best_score >= 2 else 0


def load_screaming_frog_csv(uploaded_file: Any) -> pd.DataFrame:
    raw_bytes = uploaded_file.getvalue()
    if not raw_bytes:
        raise ValueError("Le fichier CSV est vide.")

    csv_text = decode_csv(raw_bytes)
    delimiter = detect_delimiter("\n".join(csv_text.splitlines()[:5]))
    header_row = detect_header_row(csv_text, delimiter=delimiter)

    df = pd.read_csv(StringIO(csv_text), sep=delimiter, skiprows=header_row)
    df = df.dropna(axis=1, how="all")
    if df.empty:
        raise ValueError("Aucune donnée exploitable trouvée dans le CSV.")
    return df


def resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    lookup = {normalize_name(col): col for col in df.columns}
    resolved: dict[str, str] = {}

    for canonical, aliases in CANONICAL_COLUMN_ALIASES.items():
        candidates = aliases + [canonical]
        selected = None
        for alias in candidates:
            key = normalize_name(alias)
            if key in lookup:
                selected = lookup[key]
                break
        if selected is not None:
            resolved[canonical] = selected

    return resolved


def clean_text_series(df: pd.DataFrame, resolved: dict[str, str], canonical: str) -> pd.Series:
    column = resolved.get(canonical)
    if column is None:
        return pd.Series([""] * len(df), index=df.index, dtype="object")
    return df[column].fillna("").astype(str).str.strip()


def parse_locale_number(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")

    text = str(value).strip()
    if not text:
        return float("nan")

    lowered = text.lower()
    if lowered in {"nan", "none", "null", "n/a"}:
        return float("nan")

    text = text.replace("\xa0", "").replace(" ", "").replace("%", "")
    text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)

    if text.count(".") > 1:
        first = text.find(".")
        text = text[: first + 1] + text[first + 1 :].replace(".", "")

    if text in {"", "-", ".", "-."}:
        return float("nan")

    try:
        return float(text)
    except ValueError:
        return float("nan")


def parse_numeric_series(df: pd.DataFrame, resolved: dict[str, str], canonical: str) -> pd.Series:
    column = resolved.get(canonical)
    if column is None:
        return pd.Series([float("nan")] * len(df), index=df.index, dtype="float64")
    return df[column].apply(parse_locale_number)


def normalize_url_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"#.*$", "", regex=True)
        .str.replace(r"/+$", "", regex=True)
    )


def unique_url_count(url_series: pd.Series, mask: pd.Series) -> int:
    scoped_urls = url_series[mask].dropna().astype(str).str.strip()
    scoped_urls = scoped_urls[scoped_urls != ""]
    return int(scoped_urls.nunique())


def scoped_examples(url_series: pd.Series, mask: pd.Series, max_examples: int = 3) -> list[str]:
    scoped_urls = url_series[mask].dropna().astype(str).str.strip()
    scoped_urls = scoped_urls[scoped_urls != ""]
    return scoped_urls.drop_duplicates().head(max_examples).tolist()


def infer_priority(percentage: float, count: int) -> str:
    if count <= 0:
        return "Faible"
    if percentage >= 15:
        return "Haute"
    if percentage >= 5:
        return "Moyenne"
    return "Faible"


def build_scope_masks(df: pd.DataFrame, resolved: dict[str, str]) -> dict[str, pd.Series]:
    all_mask = pd.Series(True, index=df.index)
    content_type = clean_text_series(df, resolved, "content_type").str.lower()
    indexability = clean_text_series(df, resolved, "indexability").str.lower()

    html_mask = content_type.str.contains("text/html", na=False)
    if "content_type" not in resolved:
        html_mask = all_mask.copy()

    image_mask = content_type.str.contains("image/", na=False)
    if "content_type" not in resolved:
        image_mask = pd.Series(False, index=df.index)

    indexable_mask = indexability == "indexable"
    if "indexability" not in resolved:
        indexable_mask = all_mask.copy()

    html_indexable_mask = html_mask & indexable_mask

    return {
        "all": all_mask,
        "html": html_mask,
        "image": image_mask,
        "html_indexable": html_indexable_mask,
    }


def selected_scope_mask(scope_label: ScopeKey, scope_masks: dict[str, pd.Series]) -> pd.Series:
    if scope_label == "Tout le crawl":
        return scope_masks["all"]
    if scope_label == "Tout HTML":
        return scope_masks["html"]
    return scope_masks["html_indexable"]


def ticket_scope_mask(
    ticket: TicketDefinition,
    scope_label: ScopeKey,
    scope_masks: dict[str, pd.Series],
) -> tuple[pd.Series, str]:
    if ticket.scope_mode == "all_crawl":
        return scope_masks["all"], "Tout le crawl"
    if ticket.scope_mode == "html_only":
        return scope_masks["html"], "Tout HTML"
    if ticket.scope_mode == "image_only":
        return scope_masks["image"], "Images"
    return selected_scope_mask(scope_label, scope_masks), scope_label


def duplicate_mask(values: pd.Series, scope_mask: pd.Series) -> pd.Series:
    scoped_values = values.where(scope_mask, "")
    non_empty = scoped_values != ""
    duplicate = non_empty & scoped_values.duplicated(keep=False)
    return duplicate.fillna(False)


def columns_missing(resolved: dict[str, str], required: list[str]) -> list[str]:
    return [column for column in required if column not in resolved]


def evaluate_ticket(
    ticket: TicketDefinition,
    df: pd.DataFrame,
    resolved: dict[str, str],
    scope_label: ScopeKey,
    scope_masks: dict[str, pd.Series],
    include_advanced: bool,
) -> IssueRecord | None:
    if ticket.tier == "P2" and not include_advanced:
        return None

    missing = columns_missing(resolved, ticket.required_columns)
    url_series = clean_text_series(df, resolved, "url")
    base_mask, applied_scope = ticket_scope_mask(ticket, scope_label, scope_masks)
    denominator = unique_url_count(url_series, base_mask)
    if denominator == 0:
        denominator = int(base_mask.sum())

    if missing:
        reason = f"Colonnes manquantes: {', '.join(missing)}"
        return IssueRecord(
            id=ticket.id,
            name=ticket.name,
            category=ticket.category,
            status="not_evaluable",
            count=0,
            percentage=0.0,
            examples=[],
            priority="Faible",
            complexity=ticket.complexity,
            required_columns=ticket.required_columns,
            reason=reason,
            scope=applied_scope,
            tier=ticket.tier,
            constat=reason,
            recommandation="Exporter les colonnes manquantes puis relancer l'audit.",
            explication_seo="Le signal ne peut pas être calculé sans les données requises.",
        )

    text_cache = {key: clean_text_series(df, resolved, key) for key in CANONICAL_COLUMN_ALIASES}
    num_cache = {key: parse_numeric_series(df, resolved, key) for key in NUMERIC_COLUMNS}

    url_norm = normalize_url_series(text_cache["url"])
    canonical_norm = normalize_url_series(text_cache["canonical_1"])
    indexability_lower = text_cache["indexability"].str.lower()
    indexability_status_lower = text_cache["indexability_status"].str.lower()
    robots_lower = (text_cache["meta_robots_1"] + "," + text_cache["x_robots_1"]).str.lower()

    target_status_map = dict(zip(url_norm, num_cache["status_code"]))
    target_index_map = dict(zip(url_norm, indexability_lower))
    target_status = canonical_norm.map(target_status_map)
    target_index = canonical_norm.map(target_index_map)

    mask = pd.Series(False, index=df.index)

    if ticket.id == "SEO-001":
        status = num_cache["status_code"]
        mask = (status >= 400) & (status < 500)
    elif ticket.id == "SEO-002":
        status = num_cache["status_code"]
        mask = (status >= 500) & (status < 600)
    elif ticket.id == "SEO-003":
        status = num_cache["status_code"]
        mask = status.isin([302, 307])
    elif ticket.id == "SEO-004":
        mask = indexability_lower.str.contains("non indexable", na=False) & indexability_status_lower.str.contains(
            "canon", na=False
        )
    elif ticket.id == "SEO-005":
        mask = robots_lower.str.contains("noindex", na=False)
    elif ticket.id == "SEO-006":
        mask = robots_lower.str.contains("nofollow", na=False)
    elif ticket.id == "SEO-007":
        mask = canonical_norm == ""
    elif ticket.id == "SEO-008":
        mask = (canonical_norm != "") & (canonical_norm != url_norm)
    elif ticket.id == "SEO-009":
        mask = (canonical_norm != "") & target_status.notna() & (target_status != 200)
    elif ticket.id == "SEO-010":
        mask = (canonical_norm != "") & target_index.notna() & (target_index != "indexable")
    elif ticket.id == "SEO-011":
        mask = text_cache["url"].str.contains(r"\?", regex=True, na=False) & (indexability_lower == "indexable")
    elif ticket.id == "SEO-012":
        mask = text_cache["title_1"] == ""
    elif ticket.id == "SEO-013":
        mask = duplicate_mask(text_cache["title_1"], base_mask)
    elif ticket.id == "SEO-014":
        lengths = num_cache["title_1_len"]
        fallback_lengths = text_cache["title_1"].str.len().astype(float)
        lengths = lengths.fillna(fallback_lengths)
        mask = (lengths > 0) & (lengths < 30)
    elif ticket.id == "SEO-015":
        lengths = num_cache["title_1_len"]
        fallback_lengths = text_cache["title_1"].str.len().astype(float)
        lengths = lengths.fillna(fallback_lengths)
        mask = lengths > 60
    elif ticket.id == "SEO-016":
        mask = num_cache["title_1_px"] > 580
    elif ticket.id == "SEO-017":
        mask = text_cache["h1_1"] == ""
    elif ticket.id == "SEO-018":
        mask = duplicate_mask(text_cache["h1_1"], base_mask)
    elif ticket.id == "SEO-019":
        mask = text_cache["h1_2"] != ""
    elif ticket.id == "SEO-020":
        mask = text_cache["h2_1"] == ""
    elif ticket.id == "SEO-021":
        mask = text_cache["meta_desc_1"] == ""
    elif ticket.id == "SEO-022":
        mask = duplicate_mask(text_cache["meta_desc_1"], base_mask)
    elif ticket.id == "SEO-023":
        lengths = num_cache["meta_desc_1_len"]
        fallback_lengths = text_cache["meta_desc_1"].str.len().astype(float)
        lengths = lengths.fillna(fallback_lengths)
        mask = (lengths > 0) & (lengths < 70)
    elif ticket.id == "SEO-024":
        lengths = num_cache["meta_desc_1_len"]
        fallback_lengths = text_cache["meta_desc_1"].str.len().astype(float)
        lengths = lengths.fillna(fallback_lengths)
        mask = lengths > 155
    elif ticket.id == "SEO-025":
        mask = text_cache["meta_desc_2"] != ""
    elif ticket.id == "SEO-026":
        mask = num_cache["word_count"] < 200
    elif ticket.id == "SEO-027":
        mask = num_cache["text_ratio"] < 10
    elif ticket.id == "SEO-028":
        mask = num_cache["near_dup_count"] > 0
    elif ticket.id == "SEO-029":
        mask = num_cache["crawl_depth"] > 3
    elif ticket.id == "SEO-030":
        mask = num_cache["inlinks"] <= 1
    elif ticket.id == "SEO-031":
        mask = num_cache["outlinks"] == 0
    elif ticket.id == "SEO-032":
        mask = num_cache["link_score"] < 10
    elif ticket.id == "SEO-033":
        mask = num_cache["response_time"] > 1.0
    elif ticket.id == "SEO-034":
        mask = num_cache["images_without_alt"] > 0
    elif ticket.id == "SEO-035":
        code_1 = text_cache["hreflang_code_1"]
        code_2 = text_cache["hreflang_code_2"]
        code_3 = text_cache["hreflang_code_3"]
        link_1 = text_cache["hreflang_link_1"]
        link_2 = text_cache["hreflang_link_2"]
        link_3 = text_cache["hreflang_link_3"]
        mask = (
            ((code_1 != "") & (link_1 == ""))
            | ((code_2 != "") & (link_2 == ""))
            | ((code_3 != "") & (link_3 == ""))
        )
    elif ticket.id == "SEO-036":
        code_1 = text_cache["hreflang_code_1"].str.lower()
        code_2 = text_cache["hreflang_code_2"].str.lower()
        code_3 = text_cache["hreflang_code_3"].str.lower()
        code_count = (code_1 != "").astype(int) + (code_2 != "").astype(int) + (code_3 != "").astype(int)
        has_x_default = (code_1 == "x-default") | (code_2 == "x-default") | (code_3 == "x-default")
        mask = (code_count >= 2) & (~has_x_default)
    elif ticket.id == "SEO-037":
        status_lower = text_cache["inspection_status"].str.lower()
        error_lower = text_cache["inspection_error"].str.lower()
        has_status_error = status_lower.str.contains("error|erreur|invalid|fail", regex=True, na=False)
        has_error_message = error_lower != ""
        mask = has_status_error | has_error_message
    elif ticket.id == "SEO-038":
        user_canonical = normalize_url_series(text_cache["user_canonical"])
        google_canonical = normalize_url_series(text_cache["google_canonical"])
        mask = (user_canonical != "") & (google_canonical != "") & (user_canonical != google_canonical)
    elif ticket.id == "SEO-039":
        mobile_issues = text_cache["mobile_ux_issues"].str.lower()
        mask = (mobile_issues != "") & (~mobile_issues.isin(["0", "0.0", "none", "aucun", "aucune"]))
    elif ticket.id == "SEO-040":
        rich_errors_num = num_cache["rich_results_errors"]
        rich_errors_text = text_cache["rich_results_errors"].str.lower()
        mask = (rich_errors_num > 0) | (
            (rich_errors_text != "") & (~rich_errors_text.isin(["0", "0.0", "none", "aucun", "aucune"]))
        )
    elif ticket.id == "SEO-041":
        cwv = text_cache["cwv_eval"].str.lower()
        mask = (cwv != "") & (~cwv.isin(["pass", "good", "ok", "passed"]))
    elif ticket.id == "SEO-042":
        mask = num_cache["perf_score"] < 80

    scoped_mask = base_mask & mask.fillna(False)
    count = unique_url_count(url_series, scoped_mask)
    percentage = (count / denominator * 100.0) if denominator else 0.0

    if count > 0:
        status: IssueStatus = "detected"
        prefix = "Volume critique: " if percentage > 10 else ""
        constat = f"{prefix}{count} URL sur {denominator} ({percentage:.1f}%) {ticket.constat_suffix}"
    else:
        status = "ok"
        constat = f"Aucune URL impactée sur ce scénario (base évaluée: {denominator} URL)."

    return IssueRecord(
        id=ticket.id,
        name=ticket.name,
        category=ticket.category,
        status=status,
        count=int(count),
        percentage=float(percentage),
        examples=scoped_examples(url_series, scoped_mask, max_examples=3),
        priority=infer_priority(percentage, count),
        complexity=ticket.complexity,
        required_columns=ticket.required_columns,
        reason="",
        scope=applied_scope,
        tier=ticket.tier,
        constat=constat,
        recommandation=ticket.recommendation,
        explication_seo=ticket.seo_explanation,
    )


def analyze_seo_data(
    df: pd.DataFrame,
    scope_label: ScopeKey = "HTML indexables",
    include_advanced: bool = False,
) -> tuple[list[IssueRecord], dict[str, Any]]:
    resolved = resolve_columns(df)
    if "url" not in resolved:
        raise KeyError("Colonne URL introuvable (Adresse/Address).")

    scope_masks = build_scope_masks(df, resolved)
    url_series = clean_text_series(df, resolved, "url")
    selected_mask = selected_scope_mask(scope_label, scope_masks)
    selected_urls = unique_url_count(url_series, selected_mask)

    issues: list[IssueRecord] = []
    for ticket in TICKETS:
        issue = evaluate_ticket(
            ticket=ticket,
            df=df,
            resolved=resolved,
            scope_label=scope_label,
            scope_masks=scope_masks,
            include_advanced=include_advanced,
        )
        if issue is not None:
            issues.append(issue)

    metadata = {
        "resolved_columns": resolved,
        "selected_scope": scope_label,
        "selected_scope_urls": selected_urls,
        "total_rows": int(len(df)),
    }
    return issues, metadata

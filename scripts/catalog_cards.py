"""Render inert Catalogue cards independently of scan and authorization evidence."""

import html
import json


def render_catalog_cards(catalog: dict, types: list[str]) -> str:
  """Render the selected Catalogue records, including their complete type vocabulary."""
  specialties = {item["id"]: item for item in catalog.get("specialties", [])}
  cards = [
    _catalog_row(record, specialties.get(record.get("specialty"), {}))
    for record in catalog["extensions"]
  ]
  # Keep the canonical vocabulary with the selected records for static consumers.
  # Script content is raw text, so HTML escaping would survive into the parsed
  # string. Escaping "<" at the JSON level keeps it valid and cannot close the
  # element early.
  vocabulary = json.dumps(
    {
      "types": types,
    },
    sort_keys=True,
  ).replace("<", "\\u003c")
  header = (
    f'<script type="application/json" id="catalog-vocabulary">{vocabulary}</script>'
  )
  return "\n\n".join([header, *cards]) + "\n"


TRUST_LABELS = {
  "marketplace-reviewed": "Reviewed",
  "domain-reviewed": "Domain reviewed",
  "auto-scanned": "Auto-checked",
  "locally-scanned-not-bc-gov-reviewed": "Scanned only",
  "unreviewed": "Unreviewed",
}

RISK_LABELS = {
  "low": "Low access",
  "elevated": "Elevated access",
  "high": "High access",
}

ACCESS_SIGNALS = (
  ("commands", "Commands", "runs commands"),
  ("network", "Network", "reaches the network"),
  ("writes", "Writes", "writes files"),
)


def _access_signals(capabilities: dict) -> dict[str, list[str]]:
  """Reduce declared capabilities to the three access facts users compare."""
  filesystem = capabilities.get("filesystem") or {}
  return {
    "commands": list(capabilities.get("commands") or []),
    "network": list(capabilities.get("network") or []),
    "writes": list(filesystem.get("write") or []),
  }


def _catalog_row(record: dict, registry: dict | None = None) -> str:
  """Render one catalog row, escaping every author-controlled value."""
  capabilities = record["capabilities"]
  signals = _access_signals(capabilities)
  active = [key for key, _label, _phrase in ACCESS_SIGNALS if signals[key]]
  status = (record.get("checks") or {}).get("status") or "unreviewed"
  trust = TRUST_LABELS.get(status, "Unreviewed")
  risk = record.get("risk") or ""
  risk_label = RISK_LABELS.get(risk, "")
  specialty = record.get("specialty") or "community"
  registry = registry or {}
  flair = registry.get("display-flair") or registry.get("display-name") or specialty
  source_updated = (record.get("source") or {}).get("updated")
  date_label = (
    html.escape(source_updated[:10]) + " UTC" if source_updated else "Not recorded"
  )

  granted = [phrase for key, _label, phrase in ACCESS_SIGNALS if signals[key]]
  withheld = [phrase for key, _label, phrase in ACCESS_SIGNALS if not signals[key]]
  sentence = (
    f"Declared access: {_join_phrases(granted)}."
    if granted
    else ("Declares no commands, network, or file writes.")
  )
  if granted and withheld:
    sentence += f" Does not declare that it {_join_phrases(withheld)}."

  haystack = " ".join(
    [
      record["display-name"],
      record["summary"],
      record["id"],
      " ".join(record.get("legacy-ids", [])),
      record.get("notice", ""),
      record.get("moved-to", ""),
      specialty,
      record.get("type") or "",
      " ".join(record.get("maintainers") or []),
      " ".join(signals["commands"]),
      " ".join(signals["network"]),
    ]
  ).lower()

  slots = []
  for key, label, _phrase in ACCESS_SIGNALS:
    state = "is-on" if signals[key] else "is-off"
    detail = ", ".join(signals[key][:6]) if signals[key] else "not declared"
    slots.append(
      f'    <li class="cat-slot {state}" data-signal="{key}" '
      f'title="{label}: {html.escape(detail, quote=True)}">{label}</li>'
    )

  return "\n".join(
    [
      '<article class="cat-row" '
      + ("hidden " if record.get("lifecycle") != "active" else "")
      + f'data-extension-id="{html.escape(record["id"], quote=True)}"',
      f'  data-type="{html.escape(record.get("type") or "", quote=True)}"',
      f'  data-specialty="{html.escape(specialty, quote=True)}"',
      f'  data-lifecycle="{html.escape(record.get("lifecycle") or "", quote=True)}"',
      f'  data-status="{html.escape(status, quote=True)}"',
      f'  data-risk="{html.escape(risk, quote=True)}"',
      f'  data-access="{html.escape(" ".join(active), quote=True)}"',
      f'  data-haystack="{html.escape(haystack, quote=True)}">',
      '  <div class="cat-row-id">',
      f'    <h3><button type="button" class="cat-row-open">'
      f"{html.escape(record['display-name'])}</button></h3>",
      f'    <p class="cat-row-summary">{html.escape(record["summary"])}</p>',
      '    <p class="cat-row-date">'
      f"{html.escape((record.get('type') or 'Extension').title())}"
      f" · Source updated: {date_label}</p>",
      *(
        [
          '    <p class="cat-row-summary">Unavailable: '
          f"{html.escape(record['lifecycle'])}. "
          "Installation is blocked.</p>"
        ]
        if record["lifecycle"] != "active"
        else []
      ),
      "  </div>",
      f'  <p class="cat-row-domain" data-specialty="{html.escape(specialty)}">'
      f"{html.escape(flair.title() if specialty == 'community' else flair)}</p>",
      f'  <ul class="cat-slots" aria-label="{html.escape(sentence, quote=True)}">',
      *slots,
      "  </ul>",
      f'  <p class="cat-row-trust" data-status="{html.escape(status, quote=True)}">'
      f'<span class="trust-label" data-status="{html.escape(status, quote=True)}">'
      f"{html.escape(trust)}</span>"
      + (
        f'<span class="cat-row-risk" data-risk="{html.escape(risk, quote=True)}">'
        f"{html.escape(risk_label)}</span>"
        if risk in {"elevated", "high"}
        else ""
      )
      + "</p>",
      "</article>",
    ]
  )


def _join_phrases(items: list[str]) -> str:
  """Join phrases into readable prose without Oxford-comma edge cases."""
  if len(items) <= 1:
    return "".join(items)
  return f"{', '.join(items[:-1])} and {items[-1]}"

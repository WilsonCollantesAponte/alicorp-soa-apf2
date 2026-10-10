"""Exporta los contratos OpenAPI a api/openapi/ (gobierno de contratos)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app as servicios  # noqa
from esb.gateway import app as esb  # noqa
out = Path(__file__).resolve().parents[1] / "api" / "openapi"
(out / "openapi-servicios.json").write_text(json.dumps(servicios.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
(out / "openapi-esb.json").write_text(json.dumps(esb.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
print("OpenAPI exportado en", out)

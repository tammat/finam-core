from __future__ import annotations

import json
from marketcore.catalog.discovery.result import DiscoveredObject


class CatalogWriter:
    version = "CATALOG_WRITER_V1"

    def write(self, cur, objects: list[DiscoveredObject]) -> int:
        written = 0

        for obj in objects:
            payload = dict(obj.payload or {})
            payload.update({
                "object_type": obj.object_type,
                "schema_name": obj.schema_name,
                "discovery_source": obj.discovery_source,
                "discovery_version": obj.discovery_version,
                "writer_version": self.version,
                "runtime_changed": False,
                "execution_changed": False,
                "orders_changed": False,
                "fills_changed": False,
                "micro_live_allowed": False,
            })

            cur.execute("""
                INSERT INTO warehouse.analytics_asset_catalog_v1 (
                    object_id, object_name, domain, category, version,
                    purpose, owner, steward, business_value, criticality,
                    lifecycle, evidence_level, warehouse_layer,
                    source_system, source_type, source_priority,
                    source_of_truth, direct_source_available, legacy_dependency,
                    cutover_status, retention_policy,
                    rows_count, last_update,
                    health_score, health_light, validation_status,
                    verification_status, can_be_deleted,
                    knowledge_class, knowledge_stage,
                    payload, catalog_version, calculated_at, updated_at
                )
                VALUES (
                    %(object_id)s, %(object_name)s, %(domain)s, %(category)s, %(version)s,
                    %(purpose)s, %(owner)s, %(steward)s, %(business_value)s, %(criticality)s,
                    %(lifecycle)s, %(evidence_level)s, %(warehouse_layer)s,
                    %(source_system)s, %(source_type)s, %(source_priority)s,
                    %(source_of_truth)s, %(direct_source_available)s, %(legacy_dependency)s,
                    %(cutover_status)s, %(retention_policy)s,
                    %(rows_count)s, %(last_update)s,
                    %(health_score)s, %(health_light)s, %(validation_status)s,
                    %(verification_status)s, %(can_be_deleted)s,
                    %(knowledge_class)s, %(knowledge_stage)s,
                    %(payload)s::jsonb, %(catalog_version)s, now(), now()
                )
                ON CONFLICT(object_id) DO UPDATE SET
                    object_name=EXCLUDED.object_name,
                    domain=EXCLUDED.domain,
                    category=EXCLUDED.category,
                    version=EXCLUDED.version,
                    warehouse_layer=EXCLUDED.warehouse_layer,
                    source_system=EXCLUDED.source_system,
                    source_type=EXCLUDED.source_type,
                    rows_count=EXCLUDED.rows_count,
                    last_update=EXCLUDED.last_update,
                    health_score=EXCLUDED.health_score,
                    health_light=EXCLUDED.health_light,
                    validation_status=EXCLUDED.validation_status,
                    verification_status=EXCLUDED.verification_status,
                    payload=EXCLUDED.payload,
                    catalog_version=EXCLUDED.catalog_version,
                    updated_at=now()
            """, {
                "object_id": obj.object_id,
                "object_name": obj.object_name,
                "domain": obj.domain,
                "category": obj.category,
                "version": obj.discovery_version,
                "purpose": f"Discovered {obj.category.lower()} object for {obj.domain} domain",
                "owner": "Warehouse",
                "steward": "Warehouse",
                "business_value": "HIGH",
                "criticality": "PLATFORM_CORE" if obj.warehouse_layer in ("SEMANTIC", "MART", "SNAPSHOT") else "IMPORTANT",
                "lifecycle": "ACTIVE",
                "evidence_level": "PRODUCTION",
                "warehouse_layer": obj.warehouse_layer,
                "source_system": obj.source_system,
                "source_type": obj.source_type,
                "source_priority": 1,
                "source_of_truth": False,
                "direct_source_available": False,
                "legacy_dependency": False,
                "cutover_status": "SWITCHED",
                "retention_policy": "KEEP_FOREVER",
                "rows_count": obj.rows_count,
                "last_update": obj.last_update,
                "health_score": 100,
                "health_light": "GREEN",
                "validation_status": "DISCOVERED",
                "verification_status": "VERIFIED",
                "can_be_deleted": False,
                "knowledge_class": "DATA" if obj.object_type == "DATASET" else "SERVICE",
                "knowledge_stage": "PRODUCTION",
                "payload": json.dumps(payload, ensure_ascii=False),
                "catalog_version": "ANALYTICS_ASSET_CATALOG_V1",
            })
            written += 1

        return written

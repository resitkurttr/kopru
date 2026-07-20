#!/usr/bin/env python3
"""Check the current state of the provider catalog by direct import."""
import importlib.util, sys

spec = importlib.util.spec_from_file_location("provider_catalog", "/opt/data/kopru/kopru/provider_catalog.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROVIDER_CATALOG = mod.PROVIDER_CATALOG
stats = mod.get_catalog_stats()
print(f"Total providers: {stats['total_providers']}")
print(f"Free: {stats['free_providers']}")
print(f"Paid: {stats['paid_providers']}")
print(f"Service kinds: {stats['service_kinds_count']}")
print(f"Categories: {stats['categories_count']}")
print()
print("Service kind distribution:")
for k, v in sorted(stats['service_kind_distribution'].items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()
print("Category distribution:")
for k, v in sorted(stats['category_distribution'].items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()

# List all provider IDs
ids = sorted(PROVIDER_CATALOG.keys())
print(f"\nAll {len(ids)} provider IDs:")
for i, pid in enumerate(ids):
    p = PROVIDER_CATALOG[pid]
    cat = p.get('category', 'MISSING')
    print(f"  {i+1:3d}. {pid:<30s} [{cat}]")

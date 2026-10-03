#!/usr/bin/env python
"""
production_health_check.py — Operational health check script.
Verifies system liveness, dependency readiness, Prometheus metrics endpoint,
and configuration consistency.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.observability.health import check_liveness, check_readiness
from app.observability.metrics import get_metrics_summary
from app.database.session import get_async_session_context


async def run_health_checks():
    print("=" * 60)
    print("      THRESHOLD AI GOVERNANCE — PRODUCTION HEALTH CHECK")
    print("=" * 60)

    all_passed = True

    # 1. Liveness check
    print("\n[1/4] Checking Application Liveness...")
    liveness = check_liveness()
    print(f"  Status:  {liveness.get('status')}")
    print(f"  App:     {liveness.get('app')} v{liveness.get('version')}")
    if liveness.get("status") != "healthy":
        all_passed = False

    # 2. Readiness check
    print("\n[2/4] Checking Dependency Readiness...")
    try:
        async with get_async_session_context() as session:
            readiness = await check_readiness(session)
    except Exception as exc:
        print(f"  DB session open failed: {exc}")
        readiness = await check_readiness(None)

    print(f"  Overall: {readiness.get('status')}")
    for comp, info in readiness.get("components", {}).items():
        st = info.get("status")
        print(f"    - {comp.ljust(15)}: {st}")
        if st in ("down", "error", "invalid"):
            all_passed = False

    # 3. Metrics availability
    print("\n[3/4] Checking Metrics Exposition...")
    try:
        metrics_sum = get_metrics_summary()
        print(f"  Registry:    {metrics_sum.get('registry')}")
        print(f"  Content-Type: {metrics_sum.get('content_type')}")
    except Exception as exc:
        print(f"  Metrics check failed: {exc}")
        all_passed = False

    # 4. Configuration validation
    print("\n[4/4] Validating Production Configuration...")
    try:
        settings.validate_production_config(settings)
        print("  Configuration is valid for environment:", settings.ENVIRONMENT)
    except Exception as exc:
        print(f"  Configuration invalid: {exc}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(" ALL CHECKS PASSED: SYSTEM READY FOR TRAFFIC")
        print("=" * 60)
        return 0
    else:
        print(" HEALTH CHECK FAILED: ONE OR MORE ISSUES DETECTED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    code = asyncio.run(run_health_checks())
    sys.exit(code)

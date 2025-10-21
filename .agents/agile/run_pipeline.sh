#!/bin/bash
#
# PIPELINE RUNNER - Quick wrapper for pipeline orchestrator
#
# Usage:
#   ./run_pipeline.sh full card-20251021055822
#   ./run_pipeline.sh continue card-20251021055822
#   ./run_pipeline.sh architecture card-20251021055822
#   ./run_pipeline.sh dependencies card-20251021055822
#   ./run_pipeline.sh validation card-20251021055822
#   ./run_pipeline.sh arbitration card-20251021055822
#   ./run_pipeline.sh integration card-20251021055822
#   ./run_pipeline.sh testing card-20251021055822
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <full|continue|architecture|dependencies|validation|arbitration|integration|testing> <card-id>"
  exit 1
fi

MODE=$1
CARD_ID=$2

case "$MODE" in
  full)
    python3 pipeline_orchestrator.py --card-id "$CARD_ID" --full
    ;;
  continue)
    python3 pipeline_orchestrator.py --card-id "$CARD_ID" --continue
    ;;
  architecture|dependencies|validation|arbitration|integration|testing)
    python3 pipeline_orchestrator.py --card-id "$CARD_ID" --stage "$MODE"
    ;;
  *)
    echo "Invalid mode: $MODE"
    echo "Valid modes: full, continue, architecture, dependencies, validation, arbitration, integration, testing"
    exit 1
    ;;
esac

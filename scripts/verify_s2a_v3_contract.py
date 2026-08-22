from __future__ import annotations

from st_guitar_fingering_training.s2a_v3_consensus_tournament import (
    CV_MACRO_DELTA_MINIMUM,
    CV_MACRO_TOP1_MINIMUM,
    CV_MRR_MINIMUM,
    CV_TOP1_MINIMUM,
    FINAL_MACRO_DELTA_MINIMUM,
    FINAL_MACRO_TOP1_MINIMUM,
    FINAL_MRR_MINIMUM,
    FINAL_TOP1_MINIMUM,
    MAX_FEATURES,
    MIN_SAMPLES_LEAF,
    RANDOM_STATE,
    REPEAT_MINIMUM,
    TREE_COUNT,
)


def main() -> int:
    assert TREE_COUNT == 250
    assert MIN_SAMPLES_LEAF == 4
    assert MAX_FEATURES == "sqrt"
    assert RANDOM_STATE == 0
    assert REPEAT_MINIMUM == 0.80
    assert CV_TOP1_MINIMUM == 0.60
    assert CV_MRR_MINIMUM == 0.75
    assert CV_MACRO_TOP1_MINIMUM == 0.60
    assert CV_MACRO_DELTA_MINIMUM == 0.05
    assert FINAL_TOP1_MINIMUM == 0.60
    assert FINAL_MRR_MINIMUM == 0.75
    assert FINAL_MACRO_TOP1_MINIMUM == 0.60
    assert FINAL_MACRO_DELTA_MINIMUM == 0.05
    print("S2-A.v3 frozen contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

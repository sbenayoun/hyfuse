"""T2.6 tests: confounder check flags confounded clustering, clears clean one."""

import numpy as np

from hyfuse.evaluate import (
    confounder_classifier_auc,
    confounder_mutual_information,
    confounder_report,
)


def _grouped(n_groups=6, per=10, seed=0):
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(n_groups), per)
    return rng, groups


def test_mi_high_when_labels_track_confounder():
    labels = np.array([0, 0, 1, 1, 2, 2] * 5)
    conf = labels.copy()  # identical -> high MI
    mi = confounder_mutual_information(labels, conf)
    assert mi["mi"] > mi["mi_shuffle_p95"]


def test_mi_low_when_independent():
    rng = np.random.default_rng(1)
    labels = rng.integers(0, 3, size=60)
    conf = rng.integers(0, 2, size=60)  # independent
    mi = confounder_mutual_information(labels, conf)
    # observed MI should be near the shuffle baseline (not far above p95)
    assert mi["mi"] <= mi["mi_shuffle_p95"] + 0.02


def test_classifier_detects_confounder_from_features():
    # Features strongly separate the confounder -> grouped CV accuracy >> majority.
    rng, groups = _grouped(n_groups=6, per=12, seed=2)
    conf = (groups % 2)  # two confounder classes, balanced across groups
    # feature = confounder signal + noise
    feats = (conf[:, None] * 5.0 + rng.normal(size=(len(conf), 3)))
    auc = confounder_classifier_auc(feats, conf, groups, seed=0)
    assert auc["cv_accuracy"] > auc["majority_rate"] + 0.10


def test_classifier_at_chance_for_random_features():
    rng, groups = _grouped(n_groups=6, per=12, seed=3)
    conf = (groups % 2)
    feats = rng.normal(size=(len(conf), 3))  # no signal
    auc = confounder_classifier_auc(feats, conf, groups, seed=0)
    # should be near the majority rate, not clearly above
    assert auc["cv_accuracy"] <= auc["majority_rate"] + 0.15


def test_confounder_report_flags_confounded_not_clean():
    rng, groups = _grouped(n_groups=6, per=12, seed=4)
    # processing_level IS the cluster signal (confounded);
    # instrument_gen is independent noise (clean).
    proc = (groups % 2)
    labels = proc.copy()
    feats = proc[:, None] * 5.0 + rng.normal(size=(len(proc), 3))
    instr = rng.integers(0, 2, size=len(proc))
    rep = confounder_report(labels, feats,
                            {"processing_level": proc, "instrument_gen": instr},
                            groups, seed=0)
    assert rep["processing_level"]["flag_confounded"] is True
    assert rep["instrument_gen"]["flag_confounded"] is False


def test_confounder_classifier_degenerate_single_class():
    groups = np.repeat(np.arange(4), 5)
    conf = np.zeros(20, dtype=int)  # single class
    feats = np.random.default_rng(0).normal(size=(20, 2))
    auc = confounder_classifier_auc(feats, conf, groups)
    assert auc["cv_accuracy"] == auc["majority_rate"] == 1.0
    assert "degenerate" in auc.get("note", "")

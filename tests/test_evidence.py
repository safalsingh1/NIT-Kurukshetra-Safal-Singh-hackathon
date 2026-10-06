"""
tests/test_evidence.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from src.risk.evidence import compute_evidence, quick_evidence, EvidenceInput


def test_rumour_is_watch():
    result = quick_evidence(news_count=1, news_sources=1, sec_confirmed=False, social_count=0, ticker="NVDA")
    assert result.status == "WATCH"
    assert result.allow_action is False
    assert result.evidence_score < 40


def test_confirmed_event():
    result = quick_evidence(
        news_count=85, news_sources=18, sec_confirmed=True, social_count=400,
        news_sentiment=0.82, social_sentiment=0.71, ticker="NVDA"
    )
    assert result.status == "CONFIRMED"
    assert result.allow_action is True
    assert result.evidence_score >= 70


def test_developing_event():
    result = quick_evidence(
        news_count=30, news_sources=10, sec_confirmed=False, social_count=150,
        news_sentiment=-0.4, social_sentiment=-0.3, ticker="TSLA"
    )
    assert result.status in ("DEVELOPING", "CONFIRMED")
    assert 40 <= result.evidence_score


def test_sec_confirmation_boosts_score():
    without_sec = quick_evidence(news_count=20, news_sources=8, sec_confirmed=False, ticker="AAPL")
    with_sec    = quick_evidence(news_count=20, news_sources=8, sec_confirmed=True, ticker="AAPL")
    assert with_sec.evidence_score > without_sec.evidence_score


def test_score_in_range():
    result = quick_evidence(news_count=5, news_sources=3, ticker="JPM")
    assert 0 <= result.evidence_score <= 100


def test_manual_override():
    inp = EvidenceInput(ticker="TEST", manual_evidence_override=85.0)
    result = compute_evidence(inp)
    assert result.evidence_score == 85.0
    assert result.status == "CONFIRMED"

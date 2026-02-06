import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from translate_portfolio import has_pretranslated_portfolio


def test_has_pretranslated_portfolio_true_when_title_de_present():
    data = {
        "raw_data": {
            "portfolio": {
                "stocks": {
                    "NOVO-B.CO": {
                        "articles": [
                            {"title": "Title", "title_de": "Titel"}
                        ]
                    }
                }
            }
        }
    }
    assert has_pretranslated_portfolio(data) is True


def test_has_pretranslated_portfolio_false_when_missing_title_de():
    data = {
        "raw_data": {
            "portfolio": {
                "stocks": {
                    "AAPL": {
                        "articles": [
                            {"title": "Apple updates guidance"}
                        ]
                    }
                }
            }
        }
    }
    assert has_pretranslated_portfolio(data) is False

import json

import httpx
import pytest

from computer_tutor.agent import request_step
from computer_tutor.storage import Settings


def response(content):
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


def test_vision_request_and_validated_annotation():
    def handler(request):
        assert request.url == "https://api.openai.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only"
        body = json.loads(request.content)
        assert body["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;")
        return httpx.Response(
            200,
            json=response(
                {
                    "title": "Datei öffnen",
                    "explanation": "Klicke auf Datei.",
                    "done": False,
                    "annotations": [
                        {
                            "id": "menu",
                            "label": "Dateimenü",
                            "target": {
                                "x": 0.01,
                                "y": 0.02,
                                "width": 0.1,
                                "height": 0.04,
                            },
                        }
                    ],
                }
            ),
        )

    step = request_step(
        Settings(),
        "test-only",
        "Speichern",
        [],
        {"width": 1920},
        b"png",
        transport=httpx.MockTransport(handler),
    )
    assert step.annotations[0].id == "menu"
    assert not step.done


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_provider_errors_do_not_echo_keys_or_private_response_bodies(status):
    transport = httpx.MockTransport(lambda _request: httpx.Response(status, text="SECRET_API_KEY"))
    with pytest.raises(RuntimeError) as failure:
        request_step(Settings(), "SECRET_API_KEY", "goal", [], {}, b"", transport=transport)
    assert "SECRET_API_KEY" not in str(failure.value)


def test_out_of_screen_model_output_is_never_presented():
    invalid = {
        "title": "Test",
        "explanation": "Text",
        "annotations": [
            {
                "id": "invalid",
                "label": "Text",
                "target": {"x": 1.5, "y": 0, "width": 0.2, "height": 0.1},
            }
        ],
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=response(invalid)))
    with pytest.raises(RuntimeError, match="gültigen Lernschritt"):
        request_step(Settings(), "test", "goal", [], {}, b"", transport=transport)

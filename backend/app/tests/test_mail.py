from app.tasks.mail import send_email


def test_smtp_delivery_and_starttls(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr(settings, "smtp_user", "smtp-user")
    events = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self):
            events.append("tls")

        def login(self, *args):
            events.append("login")

        def send_message(self, message):
            events.append(message)

    monkeypatch.setattr("app.tasks.mail.smtplib.SMTP", SMTP)
    send_email.run("reader@example.org", "Verifica tu correo", "https://example.org/verify")
    assert events[:2] == ["tls", "login"]
    assert events[2]["To"] == "reader@example.org"
    assert "https://example.org/verify" in events[2].get_content()

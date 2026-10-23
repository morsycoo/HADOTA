from pathlib import Path

path = Path("app/web/main.py")
content = path.read_text(encoding="utf-8")

old = '''                application.state.conversation_service = service
                application.state.session_manager = SessionManager()
'''

new = '''                application.state.conversation_service = service
                session_manager = SessionManager()
                application.state.session_manager = session_manager
'''

if content.count(old) != 1:
    raise SystemExit(
        "Expected service_factory block was not found exactly once. No changes made."
    )

content = content.replace(old, new, 1)
path.write_text(content, encoding="utf-8")

print("Fixed SessionManager lifecycle in the injected service_factory path.")

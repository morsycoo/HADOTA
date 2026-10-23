from pathlib import Path
import shutil

root = Path.cwd()
destination = root / "maintenance_scripts"

names = [
    "cleanup_duplicate_test.py",
    "fix_close_all_tests.py",
    "fix_shared_runtime_factory_test.py",
    "fix_test_file_ending.py",
    "fix_test_newline.py",
    "fix_web_main_session_manager.py",
    "patch_close_all_tests.py",
    "patch_conversation_operation.py",
    "patch_conversation_operation_test.py",
    "patch_expired_cleanup_test.py",
    "patch_sessions.py",
    "patch_sessions_lifecycle.py",
    "patch_session_manager_close_all.py",
    "patch_shared_runtime_factory.py",
    "patch_shared_runtime_factory_test.py",
    "patch_web_main_close_all.py",
    "patch_web_main_lifecycle.py",
    "patch_web_shutdown_test.py",
    "repair_test_file_ending.py",
]

sources = [root / name for name in names]

missing = [str(path.name) for path in sources if not path.is_file()]
if missing:
    raise SystemExit(f"Missing source files; nothing moved: {missing}")

if destination.exists():
    conflicts = [
        name for name in names
        if (destination / name).exists()
    ]
    if conflicts:
        raise SystemExit(
            f"Destination conflicts; nothing moved: {conflicts}"
        )
else:
    destination.mkdir()

moved = []

try:
    for source in sources:
        target = destination / source.name
        shutil.move(str(source), str(target))
        moved.append(source.name)
        print(f"Moved: {source.name}")

    actual = sorted(path.name for path in destination.iterdir() if path.is_file())
    if sorted(moved) != sorted(actual):
        raise RuntimeError(
            f"Verification mismatch. Moved={len(moved)}, destination={len(actual)}"
        )

except Exception:
    print("Move failed. Attempting rollback...")
    for name in reversed(moved):
        target = destination / name
        source = root / name
        if target.exists() and not source.exists():
            shutil.move(str(target), str(source))
    raise

print(f"\nSUCCESS: verified {len(moved)} files in {destination.name}/")

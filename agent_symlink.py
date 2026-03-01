import os
import sys
from pathlib import Path


SOURCE_FILE = "AGENTS.md"
FRAMEWORK_FILES = ["CLAUDE.md", "GEMINI.md"]


def find_project_root(start_path: Path) -> Path | None:
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def ensure_agents_file(path: Path) -> tuple[bool, str]:
    """Ensure AGENTS.md exists as a regular file (not a symlink)."""
    if path.exists():
        if path.is_symlink():
            return False, "is_symlink"
        if path.is_dir():
            return False, "is_directory"
        return True, "already_exists"

    try:
        path.write_text(
            "# AGENTS\n\n"
            "Central agent instructions for this repository.\n",
            encoding="utf-8",
        )
        return True, "created"
    except OSError as exc:
        return False, f"error: {exc}"


def get_symlink_target(link_path: Path) -> str | None:
    try:
        return os.readlink(link_path)
    except OSError:
        return None


def create_file_symlink(link_path: Path, target_path: Path) -> tuple[bool, str]:
    if link_path.exists():
        if link_path.is_symlink():
            current_target = get_symlink_target(link_path)
            if current_target and os.path.normpath(current_target) == os.path.normpath(str(target_path)):
                return False, "already_correct"
            return False, "wrong_target"
        return False, "real_exists"

    try:
        os.symlink(target_path, link_path)
        return True, "created"
    except OSError as exc:
        return False, f"error: {exc}"


def main():
    print("========================================")
    print("Agent Markdown Symlink Setup")
    print("========================================")

    project_root = find_project_root(Path.cwd())
    if not project_root:
        print("\nFEHLER: Kein Git-Repository gefunden!")
        print("Bitte fuehren Sie das Skript in einem Projektverzeichnis aus.")
        sys.exit(1)

    print(f"\nProjekt: {project_root}")

    source_path = project_root / SOURCE_FILE
    links_created = 0
    skipped = 0
    warnings = 0

    print(f"\nSource-Datei: {SOURCE_FILE}")
    ok, source_status = ensure_agents_file(source_path)
    if source_status == "created":
        print(f"  + {SOURCE_FILE} erstellt")
    elif source_status == "already_exists":
        print(f"  o {SOURCE_FILE} vorhanden")
    elif source_status == "is_symlink":
        print(f"  ! WARNUNG: {SOURCE_FILE} ist ein Symlink, soll aber eine echte Datei sein.")
        print(f"    -> Ersetzen Sie den Symlink manuell durch eine echte Datei.")
        warnings += 1
    elif source_status == "is_directory":
        print(f"  ! FEHLER: {SOURCE_FILE} ist ein Ordner.")
        warnings += 1
    else:
        print(f"  ! FEHLER: {SOURCE_FILE} -> {source_status}")
        warnings += 1

    if not ok:
        print("\nAbbruch: Source-Datei ist nicht im erwarteten Zustand.")
        sys.exit(1)

    print("\nDatei-Symlinks:")
    for file_name in FRAMEWORK_FILES:
        link_path = project_root / file_name
        success, status = create_file_symlink(link_path, source_path)

        if status == "created":
            print(f"  + {file_name} -> {SOURCE_FILE}")
            links_created += 1
        elif status == "already_correct":
            print(f"  o {file_name} -> {SOURCE_FILE} (bereits korrekt)")
            skipped += 1
        elif status == "wrong_target":
            current = get_symlink_target(link_path)
            print(f"  ! WARNUNG: {file_name} zeigt auf '{current}', sollte aber auf '{SOURCE_FILE}' zeigen.")
            print(f"    -> Loeschen Sie den Symlink manuell mit: del \"{link_path}\"")
            print("    -> Dann fuehren Sie das Skript erneut aus.")
            warnings += 1
        elif status == "real_exists":
            print(f"  ! WARNUNG: {file_name} existiert bereits als echte Datei.")
            print("    -> Loeschen oder benennen Sie die Datei manuell um, um den Symlink zu erstellen.")
            print(f"    -> Beispiel: ren \"{file_name}\" \"{file_name}_backup.md\"")
            warnings += 1
        else:
            print(f"  ! FEHLER: {file_name} -> {status}")
            warnings += 1

    print("\n========================================")
    print("Zusammenfassung:")
    print(f"  - Source-Datei: {SOURCE_FILE}")
    print(f"  - Datei-Symlinks erstellt: {links_created}")
    print(f"  - Bereits korrekt/uebersprungen: {skipped}")
    print(f"  - Warnungen: {warnings}")
    print("========================================")

    if warnings > 0:
        print("\nWICHTIG: Bitte beheben Sie die Warnungen manuell.")
        print("Das Skript loescht KEINE Dateien automatisch.")
    else:
        print("\nFertig! Markdown-Symlinks wurden erstellt.")
    print("========================================")


if __name__ == "__main__":
    main()

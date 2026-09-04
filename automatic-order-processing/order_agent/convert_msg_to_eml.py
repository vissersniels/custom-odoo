from __future__ import annotations

import argparse
import mimetypes
from email import policy
from email.message import EmailMessage
from pathlib import Path

import extract_msg


def _pick_attachment_name(attachment, index: int) -> str:
    name = getattr(attachment, "longFilename", None) or getattr(attachment, "shortFilename", None)
    if name:
        return str(name)
    return f"attachment_{index}"


def _parse_mime_type(filename: str, attachment) -> tuple[str, str]:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed and "/" in guessed:
        maintype, subtype = guessed.split("/", 1)
        return maintype, subtype

    att_mime = getattr(attachment, "mimetype", None)
    if att_mime and "/" in att_mime:
        maintype, subtype = att_mime.split("/", 1)
        return maintype, subtype

    return "application", "octet-stream"


def _build_email_message(msg_path: Path) -> EmailMessage:
    msg = extract_msg.Message(str(msg_path))

    eml = EmailMessage()
    eml["From"] = msg.sender or ""

    if msg.to:
        eml["To"] = msg.to
    if msg.cc:
        eml["Cc"] = msg.cc
    if msg.subject:
        eml["Subject"] = msg.subject
    if msg.date:
        eml["Date"] = str(msg.date)

    header_dict = getattr(msg, "headerDict", None) or {}
    message_id = header_dict.get("Message-ID") or header_dict.get("Message-Id") or header_dict.get("message-id")
    if message_id:
        eml["Message-ID"] = str(message_id)

    body = msg.body or ""
    eml.set_content(body)

    for idx, attachment in enumerate(getattr(msg, "attachments", []) or [], start=1):
        data = getattr(attachment, "data", None)
        if not data:
            continue

        filename = _pick_attachment_name(attachment, idx)
        maintype, subtype = _parse_mime_type(filename, attachment)
        eml.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    msg.close()
    return eml


def convert_folder(input_dir: Path, output_dir: Path, overwrite: bool = False) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    converted = 0
    skipped = 0

    for msg_path in sorted(input_dir.glob("*.msg")):
        eml_path = output_dir / f"{msg_path.stem}.eml"
        if eml_path.exists() and not overwrite:
            skipped += 1
            print(f"SKIP  {msg_path.name} -> {eml_path.name} (already exists)")
            continue

        try:
            eml = _build_email_message(msg_path)
            eml_path.write_bytes(eml.as_bytes(policy=policy.SMTP))
            converted += 1
            print(f"OK    {msg_path.name} -> {eml_path.name}")
        except Exception as exc:  # pragma: no cover - defensive for one-off utility
            skipped += 1
            print(f"FAIL  {msg_path.name}: {type(exc).__name__}: {exc}")

    return converted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="One-time converter: Outlook .msg files to RFC2822 .eml files")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sample_emails",
        help="Folder containing .msg files (default: ../sample_emails relative to this script)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Folder to write .eml files (default: same as --input-dir)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .eml files",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    converted, skipped = convert_folder(input_dir=input_dir, output_dir=output_dir, overwrite=args.overwrite)
    print(f"Done. Converted: {converted} | Skipped/Failed: {skipped}")


if __name__ == "__main__":
    main()

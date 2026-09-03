import argparse
import json
from datetime import date

from .config import load_settings
from .ed import EdAPIError, EdClient
from .filtering import candidate_reason
from .openrouter import ExtractionError, create_digest, extract
from .store import Store


def client_from_settings(settings):
    return EdClient(settings.ed_api_token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Ed Discussion information filter")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Verify Ed authentication without revealing credentials")
    sub.add_parser("courses", help="List enrolled courses")
    threads = sub.add_parser("threads", help="Show a small thread sample")
    threads.add_argument("course_id", type=int)
    threads.add_argument("--limit", type=int, default=5)
    sync = sub.add_parser("sync", help="Import new threads and extract candidate events")
    sync.add_argument("--course", type=int, action="append", help="May be repeated")
    sync.add_argument("--all-courses", action="store_true")
    sync.add_argument("--limit", type=int, default=100)
    sub.add_parser("events", help="List locally stored extracted events")
    digest = sub.add_parser("digest", help="Create or display today's Chinese daily digest")
    digest.add_argument("--refresh", action="store_true", help="Regenerate today’s digest")
    args = parser.parse_args()
    settings = load_settings()

    try:
        if args.command == "events":
            for event in Store(settings.database_path).list_events():
                print(f"[{event['importance']}] {event['title']}: {event['summary']}")
            return
        if args.command == "digest":
            store = Store(settings.database_path)
            today = date.today().isoformat()
            existing = store.get_digest(today)
            if existing and not args.refresh:
                print(existing["content"])
                return
            events = [dict(row) for row in store.digest_events()]
            if not events:
                raise ExtractionError("No high- or medium-priority events are stored yet.")
            content = create_digest(events, settings.openrouter_api_key, settings.openrouter_model, date.today())
            store.save_digest(today, content)
            print(content)
            return
        client = client_from_settings(settings)
        if args.command == "doctor":
            print(f"Ed API authentication succeeded; {len(client.courses())} enrolled course(s) found.")
        elif args.command == "courses":
            for course in client.courses():
                print(f"{course.get('id')}\t{course.get('code', '')}\t{course.get('name', '')}")
        elif args.command == "threads":
            for thread in client.threads(args.course_id, args.limit):
                print(f"#{thread.get('number', '?')} id={thread.get('id')} [{thread.get('type', '')}] {thread.get('title', '')}")
        elif args.command == "sync":
            course_ids = args.course or ([int(c['id']) for c in client.courses()] if args.all_courses else [])
            if not course_ids:
                raise EdAPIError("Choose --all-courses or at least one --course COURSE_ID.")
            store = Store(settings.database_path)
            for course in client.courses():
                store.upsert_course(course)
            new_count = candidate_count = extracted_count = 0
            for course_id in course_ids:
                for summary in client.threads(course_id, args.limit):
                    if store.has_thread(int(summary['id'])):
                        continue
                    detail = client.thread(int(summary['id']))
                    reason = candidate_reason(detail)
                    store.add_thread(detail, reason)
                    new_count += 1
                    candidate_count += bool(reason)
            for row in store.candidates():
                result = extract(json.loads(row['raw_json']), settings.openrouter_api_key, settings.openrouter_model)
                store.save_event(row['thread_id'], result)
                extracted_count += 1
            print(f"Stored {new_count} new thread(s); {candidate_count} new candidate(s); extracted {extracted_count} event(s).")
    except (EdAPIError, ExtractionError) as exc:
        raise SystemExit(f"Error: {exc}")

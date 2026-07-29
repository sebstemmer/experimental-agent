import asyncio
from datetime import UTC
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
from email.utils import parseaddr
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from emails.models import Email, ProcessedEmail
from emails.repository import (
    create_email,
    create_processed_email,
    read_unprocessed_emails,
)
from postgres_mcp.database import (
    create_all_tables_on_start,
    get_database_session,
    require_env,
)

folder = Path("data/emails")

WHITELIST = [
    d.strip().lower() for d in require_env("EMAIL_DOMAIN_WHITELIST").split(",")
]

SUMMARY_PROMPT = (
    "Condense the email into its essential information. "
    "The summary will be used to answer questions later about what happened - "
    "keep only what is needed for that. "
    "Keep every concrete fact: dates, amounts, order and tracking numbers, "
    "names, deadlines, and anything that requires action. "
    "Drop support contact instructions, do-not-reply notices, help and "
    "unsubscribe links, marketing copy and legal footers. "
    "Use at most three sentences. "
    "Write the summary in English, even if the email is in another language. "
    "Output only the summary text: no preamble, no headings, no markdown, "
    "no commentary."
)

model = ChatOpenAI(model="gpt-5.4-nano", temperature=0.0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def parse_email(content: EmailMessage) -> Email:
    message_id = content["message-id"].strip("<>")

    sent_at = content["date"].datetime.astimezone(UTC).replace(tzinfo=None)

    body = content.get_body(preferencelist=("html",))
    text = None
    if body is not None:
        soup = BeautifulSoup(body.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)

    return Email(
        message_id=message_id,
        sender=content["from"],
        subject=content["subject"],
        sent_at=sent_at,
        text=text,
    )


def is_domain_allowed(domain: str) -> bool:
    return any(
        domain == allowed_domain or domain.endswith("." + allowed_domain)
        for allowed_domain in WHITELIST
    )


async def parse_emails() -> None:
    for file in folder.glob("*.eml"):
        content = message_from_bytes(file.read_bytes(), policy=default)

        domain = parseaddr(content["from"])[1].split("@")[-1].lower()

        if not is_domain_allowed(domain):
            print(f"Skipping email from {domain}")
            continue

        parsed_email = parse_email(content)

        print(
            f"size of email text: {len(parsed_email.text) if parsed_email.text else 0}"
        )

        async with get_database_session() as session, session.begin():
            created_email = await create_email(session, parsed_email)

            if not created_email:
                print(f"Email with message_id {parsed_email.message_id} already exists")
                continue


def format_email_for_prompt(email: Email) -> str:
    return (
        f"From: {email.sender}\n"
        f"Date: {email.sent_at}\n"
        f"Subject: {email.subject}\n\n"
        f"{email.text}"
    )


async def process_email(email: Email) -> ProcessedEmail:
    response = await model.ainvoke(
        [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": format_email_for_prompt(email)},
        ]
    )
    summary = str(response.content)

    summary_embedding = await embeddings.aembed_query(summary)

    return ProcessedEmail(
        email_id=email.id,
        summary=summary,
        summary_embedding=summary_embedding,
    )


async def process_emails() -> None:
    async with get_database_session() as session:
        emails_to_process = await read_unprocessed_emails(session)

    for email in emails_to_process:
        processed_email = await process_email(email)

        async with get_database_session() as session, session.begin():
            persisted_processed_email = await create_processed_email(
                session, processed_email
            )
            if not persisted_processed_email:
                print(f"Processed email for email_id {email.id} already exists")
                continue


async def main() -> None:
    await create_all_tables_on_start()
    await parse_emails()
    await process_emails()


asyncio.run(main())

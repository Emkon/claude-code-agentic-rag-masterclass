from pydantic import BaseModel
from app.services.tracing import get_traced_client


class DocumentMetadata(BaseModel):
    document_type: str | None = None
    topic: str | None = None
    entity: str | None = None
    year: int | None = None
    quarter: str | None = None
    language: str | None = None
    summary: str | None = None


class QueryFilters(BaseModel):
    entity: str | None = None
    year: int | None = None
    quarter: str | None = None
    document_type: str | None = None


async def extract_document_metadata(text: str) -> DocumentMetadata:
    client = get_traced_client()
    prompt = (
        "Extract structured metadata from the document excerpt below.\n"
        "Return ONLY a JSON object with these optional fields (omit fields you cannot determine):\n"
        "- document_type: type of document (e.g. \"earnings_report\", \"annual_report\", \"whitepaper\", \"contract\", \"invoice\")\n"
        "- topic: main subject in a few words\n"
        "- entity: primary company or organization name\n"
        "- year: publication year as an integer\n"
        "- quarter: \"Q1\", \"Q2\", \"Q3\", or \"Q4\" if applicable\n"
        "- language: ISO 639-1 code (e.g. \"en\")\n"
        "- summary: 1-2 sentence summary\n\n"
        f"Document excerpt:\n\"\"\"\n{text[:3000]}\n\"\"\""
    )
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=400,
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        return DocumentMetadata.model_validate_json(raw)
    except Exception as exc:
        print(f"[metadata_service] extract_document_metadata failed: {exc}")
        return DocumentMetadata()


async def extract_query_filters(query: str) -> QueryFilters:
    client = get_traced_client()
    prompt = (
        "Extract search filters from this user query. "
        "Return a JSON object with only the fields that are explicitly or strongly implied. "
        "Omit fields that are not mentioned.\n"
        "Fields: entity (company or organization name), year (integer), quarter (\"Q1\"/\"Q2\"/\"Q3\"/\"Q4\"), document_type.\n"
        f"Query: \"{query}\""
    )
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=150,
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        return QueryFilters.model_validate_json(raw)
    except Exception as exc:
        print(f"[metadata_service] extract_query_filters failed: {exc}")
        return QueryFilters()

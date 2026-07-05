import csv
import io
from fastapi.responses import StreamingResponse


def to_csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Convert a flat list-of-dicts to a CSV StreamingResponse for download.

    Args:
        rows: List of dictionaries with uniform keys (first row defines headers).
        filename: Name for the Content-Disposition header.

    Returns:
        StreamingResponse with text/csv media type and attachment disposition.
    """
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
"""YouTube Reporting API tools — bulk data exports.

The Reporting API provides daily CSV reports with comprehensive channel data.
Workflow: list report types -> create a job -> wait for reports to generate -> download.
Reports are generated daily and available for 60 days.
"""

import urllib.request

from youtube_mcp.server import auth, mcp


@mcp.tool()
def youtube_reporting_list_types() -> dict:
    """List available report types that can be scheduled.

    Common report types:
    - channel_basic_a3: User activity (views, watch time, subs)
    - channel_demographics_a1: Age/gender breakdown
    - channel_traffic_source_a3: Traffic sources
    - channel_device_os_a3: Device and OS breakdown
    - channel_combined_a3: Combined multi-dimension report
    """
    reporting = auth.build_youtube_reporting_service()
    response = reporting.reportTypes().list().execute()

    report_types = []
    for rt in response.get("reportTypes", []):
        report_types.append({
            "id": rt["id"],
            "name": rt.get("name", ""),
        })

    return {"report_types": report_types, "total": len(report_types)}


@mcp.tool()
def youtube_reporting_create_job(report_type_id: str, name: str | None = None) -> dict:
    """Schedule a reporting job. Reports will be generated daily.

    Once created, YouTube will start generating daily CSV reports for this
    report type. It may take 24-48 hours for the first report to appear.

    Args:
        report_type_id: Report type ID (from youtube_reporting_list_types)
        name: Optional human-readable name for the job
    """
    reporting = auth.build_youtube_reporting_service()

    body = {"reportTypeId": report_type_id}
    if name:
        body["name"] = name

    response = reporting.jobs().create(body=body).execute()

    return {
        "job_id": response["id"],
        "report_type_id": response.get("reportTypeId"),
        "name": response.get("name"),
        "create_time": response.get("createTime"),
    }


@mcp.tool()
def youtube_reporting_list_jobs() -> dict:
    """List all active reporting jobs."""
    reporting = auth.build_youtube_reporting_service()
    response = reporting.jobs().list().execute()

    jobs = []
    for job in response.get("jobs", []):
        jobs.append({
            "job_id": job["id"],
            "report_type_id": job.get("reportTypeId"),
            "name": job.get("name"),
            "create_time": job.get("createTime"),
        })

    return {"jobs": jobs, "total": len(jobs)}


@mcp.tool()
def youtube_reporting_list_reports(job_id: str) -> dict:
    """List available reports for a job.

    Reports are generated daily and available for 60 days.

    Args:
        job_id: Job ID (from youtube_reporting_create_job or youtube_reporting_list_jobs)
    """
    reporting = auth.build_youtube_reporting_service()
    response = reporting.jobs().reports().list(jobId=job_id).execute()

    reports = []
    for report in response.get("reports", []):
        reports.append({
            "report_id": report["id"],
            "start_time": report.get("startTime"),
            "end_time": report.get("endTime"),
            "create_time": report.get("createTime"),
            "download_url": report.get("downloadUrl"),
        })

    return {"job_id": job_id, "reports": reports, "total": len(reports)}


@mcp.tool()
def youtube_reporting_download(download_url: str) -> dict:
    """Download a report CSV.

    Returns the CSV content as text. For large reports, the content
    may be truncated.

    Args:
        download_url: Download URL from youtube_reporting_list_reports
    """
    credentials = auth.credentials
    headers = {"Authorization": f"Bearer {credentials.token}"}

    req = urllib.request.Request(download_url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        content = resp.read().decode("utf-8")

        # Parse basic info
        lines = content.strip().split("\n")
        header = lines[0] if lines else ""
        row_count = len(lines) - 1 if len(lines) > 1 else 0

        # Truncate if very large
        max_chars = 50_000
        truncated = len(content) > max_chars

        return {
            "columns": header,
            "row_count": row_count,
            "truncated": truncated,
            "content": content[:max_chars],
        }
    except Exception as e:
        return {"error": f"Failed to download report: {e}"}

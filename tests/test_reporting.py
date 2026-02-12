"""Tests for bulk reporting tools with mocked YouTube API."""

from unittest.mock import MagicMock, patch


class TestListTypes:
    @patch("youtube_mcp.tools.reporting.auth")
    def test_list_types(self, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_list_types

        mock_reporting = MagicMock()
        mock_auth.build_youtube_reporting_service.return_value = mock_reporting
        mock_reporting.reportTypes().list().execute.return_value = {
            "reportTypes": [
                {"id": "channel_basic_a3", "name": "User activity"},
                {"id": "channel_demographics_a1", "name": "Demographics"},
            ]
        }

        result = youtube_reporting_list_types()
        assert result["total"] == 2
        assert result["report_types"][0]["id"] == "channel_basic_a3"


class TestCreateJob:
    @patch("youtube_mcp.tools.reporting.auth")
    def test_create(self, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_create_job

        mock_reporting = MagicMock()
        mock_auth.build_youtube_reporting_service.return_value = mock_reporting
        mock_reporting.jobs().create().execute.return_value = {
            "id": "job123",
            "reportTypeId": "channel_basic_a3",
            "name": "My Job",
            "createTime": "2026-01-01T00:00:00Z",
        }

        result = youtube_reporting_create_job("channel_basic_a3", name="My Job")
        assert result["job_id"] == "job123"
        assert result["report_type_id"] == "channel_basic_a3"


class TestListJobs:
    @patch("youtube_mcp.tools.reporting.auth")
    def test_list(self, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_list_jobs

        mock_reporting = MagicMock()
        mock_auth.build_youtube_reporting_service.return_value = mock_reporting
        mock_reporting.jobs().list().execute.return_value = {
            "jobs": [{
                "id": "job123",
                "reportTypeId": "channel_basic_a3",
                "name": "My Job",
                "createTime": "2026-01-01T00:00:00Z",
            }]
        }

        result = youtube_reporting_list_jobs()
        assert result["total"] == 1
        assert result["jobs"][0]["job_id"] == "job123"

    @patch("youtube_mcp.tools.reporting.auth")
    def test_list_empty(self, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_list_jobs

        mock_reporting = MagicMock()
        mock_auth.build_youtube_reporting_service.return_value = mock_reporting
        mock_reporting.jobs().list().execute.return_value = {"jobs": []}

        result = youtube_reporting_list_jobs()
        assert result["total"] == 0


class TestListReports:
    @patch("youtube_mcp.tools.reporting.auth")
    def test_list_reports(self, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_list_reports

        mock_reporting = MagicMock()
        mock_auth.build_youtube_reporting_service.return_value = mock_reporting
        mock_reporting.jobs().reports().list().execute.return_value = {
            "reports": [{
                "id": "report1",
                "startTime": "2026-01-01T00:00:00Z",
                "endTime": "2026-01-02T00:00:00Z",
                "createTime": "2026-01-03T00:00:00Z",
                "downloadUrl": "https://youtubereporting.googleapis.com/report.csv",
            }]
        }

        result = youtube_reporting_list_reports("job123")
        assert result["total"] == 1
        assert result["reports"][0]["report_id"] == "report1"


class TestDownload:
    @patch("youtube_mcp.tools.reporting.auth")
    @patch("youtube_mcp.tools.reporting.urllib.request.urlopen")
    def test_download(self, mock_urlopen, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_download

        mock_creds = MagicMock()
        mock_creds.token = "test-token"
        mock_auth.credentials = mock_creds

        mock_resp = MagicMock()
        csv_content = "date,views,watch_time\n2026-01-01,100,500\n2026-01-02,200,600\n"
        mock_resp.read.return_value = csv_content.encode("utf-8")
        mock_urlopen.return_value = mock_resp

        result = youtube_reporting_download("https://example.com/report.csv")
        assert result["row_count"] == 2
        assert result["truncated"] is False
        assert "date,views,watch_time" in result["content"]

    @patch("youtube_mcp.tools.reporting.auth")
    @patch("youtube_mcp.tools.reporting.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_download_error(self, mock_urlopen, mock_auth):
        from youtube_mcp.tools.reporting import youtube_reporting_download

        mock_creds = MagicMock()
        mock_creds.token = "test-token"
        mock_auth.credentials = mock_creds

        result = youtube_reporting_download("https://example.com/report.csv")
        assert "error" in result

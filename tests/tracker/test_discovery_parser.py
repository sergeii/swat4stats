import pytest

from apps.tracker.discovery import csv_two_columns, html_ip_port, master_server_api, plain_ip_port


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"", []),
        (
            b"1.2.3.4:1234",
            [
                ("1.2.3.4", "1234"),
            ],
        ),
        (
            b"Random text before 1.2.3.4:10480 and after",
            [
                ("1.2.3.4", "10480"),
            ],
        ),
        (
            b"1.1.1.1:10480\n2.2.2.2:10580\n3.3.3.3:12345",
            [
                ("1.1.1.1", "10480"),
                ("2.2.2.2", "10580"),
                ("3.3.3.3", "12345"),
            ],
        ),
        (
            b"1.1.1.1:10480,2.2.2.2:10580,3.3.3.3:12345",
            [
                ("1.1.1.1", "10480"),
                ("2.2.2.2", "10580"),
                ("3.3.3.3", "12345"),
            ],
        ),
        (
            b" 1.1.1.1:10480 2.2.2.2:10580  3.3.3.3:12345",
            [
                ("1.1.1.1", "10480"),
                ("2.2.2.2", "10580"),
                ("3.3.3.3", "12345"),
            ],
        ),
        (
            b" 1.1.1.1:10480,256.0.0.1:12345,3.3.3.3:12345",
            [
                ("1.1.1.1", "10480"),
                ("3.3.3.3", "12345"),
            ],
        ),
        (b"256.0.0.1:80", []),
        (b"1.2.3.4 1234", []),
        (
            b"1.2.3.4:789\n1.2.3.5:1234\r\n1.2.3.6:4321",
            [
                ("1.2.3.4", "789"),
                ("1.2.3.5", "1234"),
                ("1.2.3.6", "4321"),
            ],
        ),
    ],
)
def test_plain_ip_port(content, expected):
    result = plain_ip_port(content)
    assert result == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"", []),
        (b"<span>1.2.3.4</span>:<span>1234</span>", [("1.2.3.4", "1234")]),
        (b"Random text <span>1.2.3.4</span>:<span>10480</span> and after", [("1.2.3.4", "10480")]),
        (
            b"<span>1.1.1.1</span>:<span>10480</span><br>"
            b"<span>2.2.1.2</span>:<span>10580</span><br>"
            b"<span>3.3.3.3</span>:<span>14480</span>",
            [
                ("1.1.1.1", "10480"),
                ("2.2.1.2", "10580"),
                ("3.3.3.3", "14480"),
            ],
        ),
        (
            b"<ul>"
            b"<li><span>1.1.1.1</span>:<span>10480</span></li>"
            b"<li><span>2.2.1.2</span>:<span>10580</span></li>"
            b"<li><span>3.3.3.3</span>:<span>14480</span></li>"
            b"</ul>",
            [("1.1.1.1", "10480"), ("2.2.1.2", "10580"), ("3.3.3.3", "14480")],
        ),
        (b"<span>256.1.1.1</span>:<span>10480</span>", []),
        (b"<span>1.2.3.4</span><span>10480</span>", []),
    ],
)
def test_html_ip_port(content, expected):
    result = html_ip_port(content)
    assert result == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"", []),
        (b"column1,column2", [("column1", "column2")]),
        (
            b"column1,column2\nrow1_col1,row1_col2\nrow2_col1,row2_col2",
            [("column1", "column2"), ("row1_col1", "row1_col2"), ("row2_col1", "row2_col2")],
        ),
        (
            b"column1,column2\nrow1_col1,row1_col2\nrow2_col1",
            [("column1", "column2"), ("row1_col1", "row1_col2")],
        ),
    ],
)
def test_csv_two_columns(content, expected):
    result = csv_two_columns(content)
    assert result == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"[]", []),
        (b'[{"ip": "1.2.3.4", "port": "1234"}]', [("1.2.3.4", "1234")]),
        (
            b'[{"ip": "1.2.3.4", "port": "10480"}, {"ip": "5.6.7.8", "port": "10580"}]',
            [
                ("1.2.3.4", "10480"),
                ("5.6.7.8", "10580"),
            ],
        ),
        (
            b'[{"ip": "1.2.3.4", "port": "1234"}, {"ip": "1.2.3.5", "port": "4321"}]',
            [("1.2.3.4", "1234"), ("1.2.3.5", "4321")],
        ),
    ],
)
def test_master_server_api(content, expected):
    result = master_server_api(content)
    assert result == expected
